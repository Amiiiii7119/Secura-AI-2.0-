import time
import logging
from typing import List, Tuple
import cv2
import numpy as np
from PIL import Image

from app.schemas.evidence import (
    BranchForensicResult,
    SuspiciousTemporalInterval,
    VideoAnalyzerStatus,
)
from app.services.video_sampler import SamplingResult
from app.services.video_branches.base import BaseVideoBranch
from app.services.ai_image_detector import get_ai_image_detector

logger = logging.getLogger(__name__)

class SpatialFrequencyBranch(BaseVideoBranch):
    """Branch 4: High-frequency Laplacian sensor noise variance and per-frame Swin neural diffusion distribution."""

    def __init__(self):
        super().__init__(
            analyzer_id="branch_4_spatial_frequency",
            method="High-Frequency Residual Texture & Swin Vision Transformer",
        )

    def analyze(self, sample_res: SamplingResult) -> Tuple[BranchForensicResult, List[SuspiciousTemporalInterval]]:
        start_t = time.perf_counter()
        frames = sample_res.frames
        timestamps = [f.timestamp_sec for f in frames]

        if not frames:
            return (
                BranchForensicResult(
                    analyzer_id=self.analyzer_id,
                    status=VideoAnalyzerStatus.INSUFFICIENT_DATA,
                    method=self.method,
                    frames_analyzed=0,
                    timestamps_analyzed=[],
                    raw_metrics={},
                    score=None,
                    score_semantics="P(Diffusion AI)",
                    runtime_ms=round((time.perf_counter() - start_t) * 1000.0, 2),
                    warnings=["No frames provided for spatial analysis."],
                    limitations=["Requires decoded RGB frames."],
                    evidence_summary="No frames available for spatial/frequency analysis.",
                ),
                [],
            )

        detector = get_ai_image_detector()
        ai_probs = []
        noise_vars = []
        suspicious_intervals: List[SuspiciousTemporalInterval] = []

        for idx, f in enumerate(frames):
            # High-pass Laplacian sensor noise proxy
            lap = cv2.Laplacian(f.gray, cv2.CV_32F)
            var_noise = float(np.var(lap))
            noise_vars.append(var_noise)

            # Frame-level diffusion inference without mutating detector active_head
            p_ai = 0.5
            try:
                pil_img = Image.fromarray(f.rgb)
                swin_pred = detector.predict_frame_swin(pil_img)
                if swin_pred is not None:
                    p_ai = float(swin_pred)
                else:
                    det_res = detector.detect(pil_img)
                    if det_res and det_res.probabilities:
                        p_ai = float(det_res.probabilities.get("artificial", 0.5))
            except Exception as e:
                logger.warning("Spatial frame AI inference failed at %d: %s", idx, e)

            ai_probs.append(p_ai)

            # Flag frame if high AI confidence
            if p_ai > 0.80:
                suspicious_intervals.append(
                    SuspiciousTemporalInterval(
                        start_timestamp=round(f.timestamp_sec, 3),
                        end_timestamp=round(f.timestamp_sec + 0.25, 3),
                        frame_indices=[f.frame_index],
                        branch=self.analyzer_id,
                        measured_metric=f"Frame Neural AI Probability P={p_ai*100:.1f}%",
                        threshold_or_basis="P(AI) > 80.0%",
                        explanation="Spatial generative diffusion texture detected on isolated keyframe.",
                        confidence_semantics="High Spatial Anomaly",
                        caveats="Heavily compressed or re-encoded frames may trigger false positives.",
                    )
                )

        mean_ai = float(np.mean(ai_probs))
        median_ai = float(np.median(ai_probs))
        peak_ai = float(np.max(ai_probs))
        ai_ratio = float(sum(1 for p in ai_probs if p > 0.5) / max(len(ai_probs), 1))
        mean_noise = float(np.mean(noise_vars))

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        summary = (
            f"Evaluated {len(frames)} frames with Swin AI-Image-Detector. "
            f"Median P(AI): {median_ai*100:.1f}%, Peak P(AI): {peak_ai*100:.1f}%. "
            f"AI Frame Ratio: {ai_ratio*100:.1f}%. Mean high-frequency noise variance: {mean_noise:.1f}."
        )

        return (
            BranchForensicResult(
                analyzer_id=self.analyzer_id,
                status=VideoAnalyzerStatus.COMPLETED,
                method=self.method,
                frames_analyzed=len(frames),
                timestamps_analyzed=timestamps,
                raw_metrics={
                    "mean_ai_probability": round(mean_ai, 4),
                    "median_ai_probability": round(median_ai, 4),
                    "peak_ai_probability": round(peak_ai, 4),
                    "ai_frame_ratio": round(ai_ratio, 4),
                    "mean_noise_variance": round(mean_noise, 2),
                    "per_frame_ai_probs": [round(p, 4) for p in ai_probs],
                    "per_frame_noise_vars": [round(n, 2) for n in noise_vars],
                },
                score=round(mean_ai, 4),
                score_semantics="Mean Spatial P(AI) across Decoded Frames",
                model_version=detector.model_name,
                runtime_ms=round(elapsed_ms, 2),
                warnings=[],
                limitations=[
                    "Image-space classifier evaluated independently per frame; lacks temporal curvature modeling.",
                    "Video compression macroblocks can mimic diffusion noise textures."
                ],
                evidence_summary=summary,
            ),
            suspicious_intervals,
        )
