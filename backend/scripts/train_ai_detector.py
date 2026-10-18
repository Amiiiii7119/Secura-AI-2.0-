#!/usr/bin/env python3
"""Secura AI 2.0 - AI Image Detection Head Training Pipeline.

Trains a regularized linear classification head (w, b) on extracted 768-dimensional
features. Strictly isolates training, validation, and held-out test splits.
Outputs trained weights to backend/models/weights/custom_fc_weights.pth.
"""

import argparse
import io
import json
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure backend root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid function."""
    z_clipped = np.clip(z, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-z_clipped))


class RegularizedLinearTrainer:
    """Trains an L2-regularized logistic classification head using Adam optimization."""

    def __init__(
        self,
        feature_dim: int = 768,
        l2_reg: float = 1e-3,
        learning_rate: float = 0.05,
        max_epochs: int = 500,
        tolerance: float = 1e-6
    ):
        self.feature_dim = feature_dim
        self.l2_reg = l2_reg
        self.lr = learning_rate
        self.max_epochs = max_epochs
        self.tolerance = tolerance

        self.w: np.ndarray = np.zeros(feature_dim, dtype=np.float32)
        self.b: float = 0.0
        self.best_w: np.ndarray = np.zeros(feature_dim, dtype=np.float32)
        self.best_b: float = 0.0
        self.best_val_acc: float = -1.0
        self.training_history: List[Dict[str, float]] = []

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """Fit weights using Adam optimizer."""
        N, D = X_train.shape
        assert D == self.feature_dim, f"Feature dimension mismatch: {D} != {self.feature_dim}"

        # Initialize with small random weights
        rng = np.random.RandomState(42)
        self.w = rng.normal(0, 0.01, size=D).astype(np.float32)
        self.b = 0.0

        # Adam optimizer state
        m_w, v_w = np.zeros_like(self.w), np.zeros_like(self.w)
        m_b, v_b = 0.0, 0.0
        beta1, beta2, eps = 0.9, 0.999, 1e-8

        prev_loss = float("inf")
        self.best_val_acc = -1.0
        self.best_w = self.w.copy()
        self.best_b = self.b

        for epoch in range(1, self.max_epochs + 1):
            # Forward pass
            logits = np.dot(X_train, self.w) + self.b
            probs = sigmoid(logits)

            # Binary cross-entropy + L2 loss
            bce_loss = -np.mean(y_train * np.log(probs + 1e-9) + (1.0 - y_train) * np.log(1.0 - probs + 1e-9))
            reg_loss = 0.5 * self.l2_reg * np.sum(self.w ** 2)
            loss = float(bce_loss + reg_loss)

            # Gradients
            diff = (probs - y_train) / N # (N,)
            grad_w = np.dot(X_train.T, diff) + self.l2_reg * self.w
            grad_b = float(np.sum(diff))

            # Adam update
            m_w = beta1 * m_w + (1.0 - beta1) * grad_w
            v_w = beta2 * v_w + (1.0 - beta2) * (grad_w ** 2)
            m_b = beta1 * m_b + (1.0 - beta1) * grad_b
            v_b = beta2 * v_b + (1.0 - beta2) * (grad_b ** 2)

            m_w_hat = m_w / (1.0 - beta1 ** epoch)
            v_w_hat = v_w / (1.0 - beta2 ** epoch)
            m_b_hat = m_b / (1.0 - beta1 ** epoch)
            v_b_hat = v_b / (1.0 - beta2 ** epoch)

            self.w -= (self.lr * m_w_hat / (np.sqrt(v_w_hat) + eps)).astype(np.float32)
            self.b -= float(self.lr * m_b_hat / (np.sqrt(v_b_hat) + eps))

            # Compute accuracies
            train_preds = (probs >= 0.5).astype(int)
            train_acc = float(np.mean(train_preds == y_train))

            val_acc = 0.0
            if X_val is not None and y_val is not None and len(y_val) > 0:
                val_logits = np.dot(X_val, self.w) + self.b
                val_preds = (sigmoid(val_logits) >= 0.5).astype(int)
                val_acc = float(np.mean(val_preds == y_val))
                if val_acc > self.best_val_acc:
                    self.best_val_acc = val_acc
                    self.best_w = self.w.copy()
                    self.best_b = self.b
            else:
                self.best_w = self.w.copy()
                self.best_b = self.b

            self.training_history.append({
                "epoch": epoch,
                "loss": round(loss, 6),
                "train_acc": round(train_acc, 4),
                "val_acc": round(val_acc, 4),
            })

            if abs(prev_loss - loss) < self.tolerance:
                break
            prev_loss = loss

        # Set final weights to best validation model
        self.w = self.best_w
        self.b = self.best_b

        return {
            "converged_epoch": epoch,
            "final_loss": round(loss, 6),
            "train_acc": round(train_acc, 4),
            "best_val_acc": round(self.best_val_acc, 4) if self.best_val_acc >= 0 else None,
            "weight_norm": round(float(np.linalg.norm(self.w)), 4),
            "bias": round(float(self.b), 6)
        }


def save_weights_torch_format(output_path: Path, w: np.ndarray, b: float) -> None:
    """Save weights in PyTorch zip container format compatible with AIImageDetectorService."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # PyTorch zip file format for fc_weights:
    # fc_weights/data/0: weight buffer float32
    # fc_weights/data/1: bias buffer float32
    w_bytes = w.astype(np.float32).tobytes()
    b_bytes = np.array([b], dtype=np.float32).tobytes()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr("fc_weights/data/0", w_bytes)
        z.writestr("fc_weights/data/1", b_bytes)
    print(f"Saved trained head weights to {output_path} ({os.path.getsize(output_path)} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Train Secura AI 2.0 AI Detection Classification Head")
    parser.add_argument(
        "--features",
        default="data/ai_detection/features/cached_features.npz",
        help="Path to cached features archive"
    )
    parser.add_argument(
        "--output",
        default="backend/models/weights/custom_fc_weights.pth",
        help="Path to save trained weights"
    )
    parser.add_argument("--l2-reg", type=float, default=1e-3, help="L2 regularization parameter")
    parser.add_argument("--epochs", type=int, default=300, help="Maximum epochs")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    features_p = project_root / args.features
    output_p = project_root / args.output

    if not features_p.exists():
        print(f"Error: Features file {features_p} not found. Run extract_ai_features.py first.")
        sys.exit(1)

    data = np.load(features_p)
    features = data["features"]
    labels = data["labels"]
    splits = data["splits"]

    # Partition splits strictly
    train_mask = splits == "train"
    val_mask = splits == "val"
    test_mask = splits == "test"

    X_train, y_train = features[train_mask], labels[train_mask]
    X_val, y_val = features[val_mask], labels[val_mask]
    X_test, y_test = features[test_mask], labels[test_mask]

    print(f"Dataset Partitions:")
    print(f"  Train:      {len(X_train)} samples ({sum(y_train==0)} Real, {sum(y_train==1)} AI)")
    print(f"  Validation: {len(X_val)} samples ({sum(y_val==0)} Real, {sum(y_val==1)} AI)")
    print(f"  Held-out:   {len(X_test)} samples ({sum(y_test==0)} Real, {sum(y_test==1)} AI)")

    print(f"\nFitting Regularized Linear Head (L2={args.l2_reg}, epochs={args.epochs})...")
    trainer = RegularizedLinearTrainer(feature_dim=768, l2_reg=args.l2_reg, max_epochs=args.epochs)
    results = trainer.fit(X_train, y_train, X_val, y_val)

    print(f"Training completed at epoch {results['converged_epoch']}:")
    print(f"  Final Loss:    {results['final_loss']}")
    print(f"  Train Acc:     {results['train_acc'] * 100:.1f}%")
    print(f"  Val Acc:       {results['best_val_acc'] * 100 if results['best_val_acc'] else 0:.1f}%")
    print(f"  Weight Norm:   {results['weight_norm']}")
    print(f"  Bias Scalar:   {results['bias']}")

    save_weights_torch_format(output_p, trainer.w, trainer.b)


if __name__ == "__main__":
    main()
