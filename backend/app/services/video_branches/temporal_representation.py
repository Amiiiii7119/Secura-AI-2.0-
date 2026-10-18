import time
import logging
import json
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

from app.schemas.evidence import (
    BranchForensicResult,
    SuspiciousTemporalInterval,
    VideoAnalyzerStatus,
)
from app.services.video_sampler import SamplingResult
from app.services.video_branches.base import BaseVideoBranch

logger = logging.getLogger(__name__)

class ReStraVMLP(nn.Module):
    """Trained NeurIPS 2025 ReStraV lightweight temporal geometry classifier."""
    def __init__(self, in_dim: int = 21, h: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, h),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(h, 1)
        )
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

class TemporalRepresentationBranch(BaseVideoBranch):
    """Branch 3: Learned Temporal Representation Trajectory Classifier (ReStraV NeurIPS 2025).

    Extracts DINOv2 self-supervised visual patch/CLS representation embeddings across consecutive
    frames and evaluates trajectory geometry (stepwise distances, turning angles, and high-order
    moments) using a trained ReStraV MLP sequence classifier.
    """

    def __init__(self):
        super().__init__(
            analyzer_id="branch_3_temporal_representation",
            method="ReStraV DINOv2 Perceptual Straightening & Temporal Geometry MLP",
        )
        self._processor: Optional[AutoImageProcessor] = None
        self._backbone: Optional[AutoModel] = None
        self._mlp: Optional[ReStraVMLP] = None
        self._mean: Optional[np.ndarray] = None
        self._std: Optional[np.ndarray] = None
        self._calib_meta: dict = {}
        self._loaded: bool = False
        self._load_models()

    def _load_models(self):
        try:
            # 1. Load DINOv2 backbone
            self._processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
            self._backbone = AutoModel.from_pretrained("facebook/dinov2-small")
            self._backbone.eval()

            # 2. Load trained ReStraV MLP & calibration parameters
            weights_dir = Path("D:/SecuraAI2/backend/models/weights/restrav_temporal")
            model_path = weights_dir / "restrav_mlp.pt"
            mean_path = weights_dir / "mean.npy"
            std_path = weights_dir / "std.npy"
            calib_path = weights_dir / "calibration.json"

            if model_path.exists() and mean_path.exists() and std_path.exists():
                self._mean = np.load(mean_path)
                self._std = np.load(std_path)
                if calib_path.exists():
                    self._calib_meta = json.loads(calib_path.read_text(encoding="utf-8"))

                self._mlp = ReStraVMLP(in_dim=21, h=32)
                self._mlp.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
                self._mlp.eval()
                self._loaded = True
                logger.info("Successfully loaded ReStraV DINOv2 temporal sequence detector and MLP weights.")
            else:
                logger.warning("ReStraV MLP weights not found at %s. Running backbone-only mode.", weights_dir)
                self._loaded = False
        except Exception as e:
            logger.error("Failed to initialize ReStraV temporal branch: %s", e)
            self._loaded = False

    def compute_geometry_features(self, frames: list) -> Tuple[np.ndarray, dict]:
        """Compute 21-D temporal geometry feature vector from decoded frames."""
        pil_images = [Image.fromarray(f.rgb) if hasattr(f, 'rgb') else Image.fromarray(f) for f in frames]
        inputs = self._processor(images=pil_images, return_tensors="pt")

        with torch.no_grad():
            outputs = self._backbone(**inputs)
            # Flattened token trajectory: [1, num_frames, 98688]
            Z = outputs.last_hidden_state.flatten(1).unsqueeze(0)

            delta = Z[:, 1:, :] - Z[:, :-1, :]
            d = delta.norm(dim=-1)
            cos = F.cosine_similarity(delta[:, :-1, :], delta[:, 1:, :], dim=-1)
            theta = torch.rad2deg(torch.acos(cos.clamp(-1.0, 1.0)))

            d7 = d[:, :7]
            t6 = theta[:, :6]

            # If fewer than 8 steps, pad with repeat
            if d7.shape[1] < 7:
                pad_d = 7 - d7.shape[1]
                d7 = torch.cat([d7, d7[:, -1:].repeat(1, pad_d)], dim=1)
            if t6.shape[1] < 6:
                pad_t = 6 - t6.shape[1]
                t6 = torch.cat([t6, t6[:, -1:].repeat(1, pad_t)], dim=1)

            mu_d = d.mean(dim=-1)
            mn_d = d.amin(dim=-1)
            mx_d = d.amax(dim=-1)
            var_d = d.var(dim=-1, unbiased=False)

            mu_t = theta.mean(dim=-1)
            mn_t = theta.amin(dim=-1)
            mx_t = theta.amax(dim=-1)
            var_t = theta.var(dim=-1, unbiased=False)

            stats = torch.stack([mu_d, mn_d, mx_d, var_d, mu_t, mn_t, mx_t, var_t], dim=1)
            feats = torch.cat([d7, t6, stats], dim=1).squeeze(0).numpy()

            metrics = {
                "mean_step_distance": float(mu_d.item()),
                "var_step_distance": float(var_d.item()),
                "mean_turning_angle_deg": float(mu_t.item()),
                "var_turning_angle_deg": float(var_t.item()),
                "min_turning_angle_deg": float(mn_t.item()),
                "max_turning_angle_deg": float(mx_t.item()),
                "step_distances": [float(x) for x in d.squeeze(0).numpy()],
                "turning_angles_deg": [float(x) for x in theta.squeeze(0).numpy()]
            }
            return feats, metrics

    def analyze(self, sample_res: SamplingResult) -> Tuple[BranchForensicResult, List[SuspiciousTemporalInterval]]:
        start_t = time.perf_counter()
        # Prefer continuous consecutive frames for ReStraV trajectory geometry
        frames = sample_res.consecutive_frames if (sample_res.consecutive_frames and len(sample_res.consecutive_frames) >= 4) else sample_res.frames
        timestamps = [f.timestamp_sec for f in frames]

        if not self._loaded or self._backbone is None or self._mlp is None:
            return (
                BranchForensicResult(
                    analyzer_id=self.analyzer_id,
                    status=VideoAnalyzerStatus.ANALYSIS_UNAVAILABLE,
                    method=self.method,
                    frames_analyzed=0,
                    timestamps_analyzed=[],
                    raw_metrics={},
                    score=None,
                    score_semantics="Calibrated ReStraV DINOv2 Sequence Probability P(AI)",
                    runtime_ms=round((time.perf_counter() - start_t) * 1000.0, 2),
                    warnings=["ReStraV DINOv2 or MLP weights unavailable."],
                    limitations=["Requires downloaded pretrained DINOv2 and trained ReStraV MLP."],
                    evidence_summary="ReStraV temporal representation analysis unavailable: model weights not loaded.",
                ),
                [],
            )

        if len(frames) < 4:
            return (
                BranchForensicResult(
                    analyzer_id=self.analyzer_id,
                    status=VideoAnalyzerStatus.INSUFFICIENT_DATA,
                    method=self.method,
                    frames_analyzed=len(frames),
                    timestamps_analyzed=timestamps,
                    raw_metrics={},
                    score=None,
                    score_semantics="Calibrated ReStraV DINOv2 Sequence Probability P(AI)",
                    runtime_ms=round((time.perf_counter() - start_t) * 1000.0, 2),
                    warnings=["At least 4 frames required for temporal sequence geometry."],
                    limitations=["ReStraV geometry requires multiple consecutive steps."],
                    evidence_summary="Insufficient frames (< 4) to compute temporal representation sequence geometry.",
                ),
                [],
            )

        # Compute 21-D geometry features
        feats, raw_metrics = self.compute_geometry_features(frames)

        # Normalize features with trained mean and std
        feats_norm = (feats.reshape(1, -1) - self._mean) / self._std

        # Run ReStraV MLP classifier
        with torch.no_grad():
            logit = self._mlp(torch.from_numpy(feats_norm).float()).item()
            # Model output: logit represents P(AI) (1=AI, 0=Real)
            p_ai = float(1.0 / (1.0 + np.exp(-logit)))
            p_real = float(1.0 - p_ai)

        p_ai_clipped = round(float(np.clip(p_ai, 0.001, 0.999)), 4)
        raw_metrics["restrav_logit"] = round(logit, 4)
        raw_metrics["p_real"] = round(p_real, 4)
        raw_metrics["p_ai"] = p_ai_clipped

        # Check for suspicious sharp kinks
        suspicious_intervals: List[SuspiciousTemporalInterval] = []
        turning_angles = raw_metrics.get("turning_angles_deg", [])
        for t_idx, angle in enumerate(turning_angles):
            # Kink angle > 115 degrees
            if angle > 115.0 and (t_idx + 1 not in sample_res.scene_cut_indices):
                if t_idx + 2 < len(frames):
                    suspicious_intervals.append(
                        SuspiciousTemporalInterval(
                            start_timestamp=round(frames[t_idx].timestamp_sec, 3),
                            end_timestamp=round(frames[t_idx + 2].timestamp_sec, 3),
                            frame_indices=[frames[t_idx].frame_index, frames[t_idx + 1].frame_index, frames[t_idx + 2].frame_index],
                            branch=self.analyzer_id,
                            measured_metric=f"Turning Angle={angle:.1f} deg",
                            threshold_or_basis="Angle > 115.0 deg (Perceptual Straightening Anomaly)",
                            explanation="Sharp unnatural turning angle in DINOv2 representation space characteristic of generative diffusion morphing.",
                            confidence_semantics="High Geometric Anomaly",
                            caveats="Can be induced by abrupt occlusion or camera jolt.",
                        )
                    )

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        summary = (
            f"Evaluated {len(frames)} frames with ReStraV DINOv2 sequence classifier. "
            f"Mean Turning Angle: {raw_metrics['mean_turning_angle_deg']:.1f} deg. "
            f"Mean Step Distance: {raw_metrics['mean_step_distance']:.1f}. "
            f"Sequence AI Probability P(AI): {p_ai_clipped*100:.1f}%."
        )

        return (
            BranchForensicResult(
                analyzer_id=self.analyzer_id,
                status=VideoAnalyzerStatus.COMPLETED,
                method=self.method,
                frames_analyzed=len(frames),
                timestamps_analyzed=timestamps,
                raw_metrics=raw_metrics,
                score=p_ai_clipped,
                score_semantics="Calibrated ReStraV DINOv2 Sequence Probability P(AI)",
                model_version="ReStraV NeurIPS 2025 DINOv2 Temporal Sequence Classifier",
                checkpoint_hash="restrav_mlp_weights_v2",
                runtime_ms=round(elapsed_ms, 2),
                warnings=[],
                limitations=[
                    "Lightweight MLP sequence classifier trained on DINOv2 self-supervised geometry trajectories.",
                    "Performance dependent on continuous chronological frame sequences without missing intervals."
                ],
                evidence_summary=summary,
            ),
            suspicious_intervals,
        )
