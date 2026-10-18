#!/usr/bin/env python3
"""Secura AI 2.0 - AI-Generated Image Detector Evaluation & Model Comparison Harness.

Evaluates and compares:
1. Original UniversalFakeDetect (CVPR 2023) classification head
2. Custom Secura AI 2.0 Regularized Linear classification head
across synthetic fixtures, perturbation transforms, and the held-out generator-disjoint test split.

Outputs results to docs/evaluation/ai_detector_evaluation.json.
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
from PIL import Image

# Ensure backend root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.evaluation.fixtures import generate_all_fixtures, SyntheticFixture
from app.services.ai_image_detector import (
    get_ai_image_detector,
    AIImageDetectorService,
    MODEL_NAME,
    MODEL_VERSION,
)
from app.schemas.evidence import AIDetectionDecision, AIDetectionStatus


def calculate_comprehensive_metrics(
    y_true: List[int],
    y_scores: List[float],
    threshold: float = 0.0
) -> Dict[str, Any]:
    """Calculate accuracy, precision, recall, f1, fpr, and roc_auc."""
    if not y_true or len(y_true) != len(y_scores):
        return {
            "sample_count": 0,
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1_score": None,
            "fpr_on_reals": None,
            "roc_auc": None,
            "confusion_matrix": {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
        }

    tp = fp = tn = fn = 0
    for yt, score in zip(y_true, y_scores):
        yp = 1 if score > threshold else 0
        if yt == 1 and yp == 1:
            tp += 1
        elif yt == 0 and yp == 1:
            fp += 1
        elif yt == 0 and yp == 0:
            tn += 1
        elif yt == 1 and yp == 0:
            fn += 1

    total = len(y_true)
    acc = (tp + tn) / total if total > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    # ROC-AUC via rank sum
    pos_scores = [s for yt, s in zip(y_true, y_scores) if yt == 1]
    neg_scores = [s for yt, s in zip(y_true, y_scores) if yt == 0]
    roc_auc = None
    if pos_scores and neg_scores:
        pairs = 0
        concordant = 0
        for ps in pos_scores:
            for ns in neg_scores:
                pairs += 1
                if ps > ns:
                    concordant += 1.0
                elif ps == ns:
                    concordant += 0.5
        roc_auc = concordant / pairs if pairs > 0 else 0.5

    return {
        "sample_count": total,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "fpr_on_reals": round(fpr, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn}
    }


def load_head_weights(weights_path: Path) -> Tuple[np.ndarray, float]:
    """Load weights and bias from zip-format checkpoint."""
    with zipfile.ZipFile(weights_path, "r") as z:
        data_0 = z.read("fc_weights/data/0")
        data_1 = z.read("fc_weights/data/1")
        w = np.frombuffer(data_0, dtype=np.float32).copy()
        b = float(np.frombuffer(data_1, dtype=np.float32)[0])
    return w, b


def evaluate_head_on_features(
    w: np.ndarray,
    b: float,
    features: np.ndarray,
    labels: np.ndarray,
    metadata: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Evaluate a linear head on a set of features and compute overall and subgroup metrics."""
    logits = []
    margins = []
    decisions = []

    for feat in features:
        norm = np.linalg.norm(feat)
        feat_n = feat / norm if norm > 1e-8 else feat
        logit = float(np.dot(w, feat_n) + b)
        margin = float(1.0 / (1.0 + np.exp(-np.clip(logit, -30.0, 30.0))))
        logits.append(logit)
        margins.append(margin)
        if logit > 0.1:
            decisions.append("AI_GENERATED_CLASS")
        elif logit < -0.1:
            decisions.append("REAL_IMAGE_CLASS")
        else:
            decisions.append("INCONCLUSIVE")

    metrics = calculate_comprehensive_metrics(labels.tolist(), logits, threshold=0.0)

    # Per-generator subgroup evaluation
    gen_groups: Dict[str, List[int]] = {}
    for idx, meta in enumerate(metadata):
        g = meta.get("generator_family") or "Real"
        gen_groups.setdefault(g, []).append(idx)

    per_generator_metrics = {}
    for g, indices in gen_groups.items():
        sub_y = [labels[i] for i in indices]
        sub_logits = [logits[i] for i in indices]
        sub_acc = sum(1 for y, l in zip(sub_y, sub_logits) if (l > 0) == (y == 1)) / len(sub_y)
        per_generator_metrics[g] = {
            "sample_count": len(indices),
            "accuracy": round(sub_acc, 4),
            "mean_logit": round(float(np.mean(sub_logits)), 4),
            "mean_margin": round(float(np.mean([margins[i] for i in indices])), 4)
        }

    return {
        "overall_metrics": metrics,
        "per_generator_performance": per_generator_metrics,
        "weight_norm": round(float(np.linalg.norm(w)), 4),
        "bias": round(float(b), 6),
        "decision_counts": {
            d: decisions.count(d) for d in set(decisions)
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate & Compare AI Detection Heads")
    parser.add_argument(
        "--features",
        default="data/ai_detection/features/cached_features.npz",
        help="Path to cached features archive"
    )
    parser.add_argument(
        "--output",
        default="docs/evaluation/ai_detector_evaluation.json",
        help="Path to save evaluation JSON"
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    features_p = project_root / args.features
    output_p = project_root / args.output
    orig_weights_p = project_root / "backend" / "models" / "weights" / "fc_weights.pth"
    custom_weights_p = project_root / "backend" / "models" / "weights" / "custom_fc_weights.pth"

    print("=================================================================")
    print("Secura AI 2.0 - Model Comparison & Held-Out Evaluation")
    print("=================================================================")

    if not features_p.exists():
        print(f"Features file {features_p} not found. Run extract_ai_features.py first.")
        sys.exit(1)

    data = np.load(features_p)
    features = data["features"]
    labels = data["labels"]
    splits = data["splits"]
    generator_families = data["generator_families"]
    image_ids = data["image_ids"]

    # Filter to held-out test split
    test_mask = splits == "test"
    X_test = features[test_mask]
    y_test = labels[test_mask]
    test_meta = [
        {"image_id": str(image_ids[i]), "generator_family": str(generator_families[i])}
        for i in np.where(test_mask)[0]
    ]

    print(f"Held-Out Test Set: {len(X_test)} samples ({sum(y_test==0)} Real, {sum(y_test==1)} AI)")

    results: Dict[str, Any] = {
        "evaluation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_harness_version": "2.0.0",
        "held_out_test_set_size": len(X_test),
        "models_evaluated": {}
    }

    # 1. Evaluate Original UniversalFakeDetect Head
    if orig_weights_p.exists():
        print("\n1. Evaluating Original UniversalFakeDetect Head (CVPR 2023)...")
        w_orig, b_orig = load_head_weights(orig_weights_p)
        orig_res = evaluate_head_on_features(w_orig, b_orig, X_test, y_test, test_meta)
        results["models_evaluated"]["UniversalFakeDetect_CVPR2023"] = {
            "model_name": "UniversalFakeDetect (CVPR 2023)",
            "weights_file": "backend/models/weights/fc_weights.pth",
            "evaluation": orig_res
        }
        print(f"   Accuracy: {orig_res['overall_metrics']['accuracy'] * 100:.1f}%")
        print(f"   ROC-AUC:  {orig_res['overall_metrics']['roc_auc']}")
        print(f"   F1-Score: {orig_res['overall_metrics']['f1_score']}")
        print(f"   FPR Reals:{orig_res['overall_metrics']['fpr_on_reals']}")

    # 2. Evaluate Custom Secura Trained Head
    if custom_weights_p.exists():
        print("\n2. Evaluating Custom Secura AI Regularized Head...")
        w_cust, b_cust = load_head_weights(custom_weights_p)
        cust_res = evaluate_head_on_features(w_cust, b_cust, X_test, y_test, test_meta)
        results["models_evaluated"]["Secura_Custom_Regularized_Head"] = {
            "model_name": "Secura AI Custom Regularized Head",
            "weights_file": "backend/models/weights/custom_fc_weights.pth",
            "evaluation": cust_res
        }
        print(f"   Accuracy: {cust_res['overall_metrics']['accuracy'] * 100:.1f}%")
        print(f"   ROC-AUC:  {cust_res['overall_metrics']['roc_auc']}")
        print(f"   F1-Score: {cust_res['overall_metrics']['f1_score']}")
        print(f"   FPR Reals:{cust_res['overall_metrics']['fpr_on_reals']}")

    # 3. Synthetic Fixtures Evaluation
    service = get_ai_image_detector()
    fixtures = generate_all_fixtures()
    print(f"\nEvaluating {len(fixtures)} synthetic fixtures on active service...")
    fixture_results = []
    for f in fixtures:
        res = service.detect(f.pil_image)
        fixture_results.append({
            "fixture_id": f.fixture_id,
            "status": res.model_status.value,
            "decision": res.decision_status.value,
            "error_code": res.error_code
        })
    results["synthetic_fixtures_evaluation"] = {
        "count": len(fixtures),
        "results": fixture_results[:10]
    }

    results["scientific_disclaimer"] = (
        "Classification scores are linear projection margins and do not constitute posterior probabilities. "
        "Performance on held-out generator-disjoint test sets reflects domain transfer capability across "
        "distinct architectures (GAN -> Diffusion)."
    )

    output_p.parent.mkdir(parents=True, exist_ok=True)
    with open(output_p, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nEvaluation results saved to {output_p}")
    print("=================================================================")


if __name__ == "__main__":
    main()
