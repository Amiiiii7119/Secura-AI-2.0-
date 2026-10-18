import time
from typing import List, Tuple
import numpy as np
from app.schemas.evidence import (
    BranchForensicResult,
    SuspiciousTemporalInterval,
    VideoAnalyzerStatus,
)
from app.services.video_sampler import SamplingResult
from app.services.video_branches.base import BaseVideoBranch

class RGBChromaticBranch(BaseVideoBranch):
    """Branch 1: Macro-temporal chromatic decomposition, color distribution trajectories, and jitter."""

    def __init__(self):
        super().__init__(analyzer_id="branch_1_rgb", method="Deterministic Temporal Chromatic Decomposition")

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
                    score_semantics="Chromatic Jitter Index",
                    runtime_ms=round((time.perf_counter() - start_t) * 1000.0, 2),
                    warnings=["No frames available for chromatic analysis."],
                    limitations=["Requires at least 2 decoded frames."],
                    evidence_summary="Zero frames decoded from video container.",
                ),
                [],
            )

        r_means, g_means, b_means = [], [], []
        r_stds, g_stds, b_stds = [], [], []
        deltas = []
        prev_gray = None

        for f in frames:
            # OpenCV BGR to normalized channels
            b_norm = f.bgr[:, :, 0].astype(np.float32) / 255.0
            g_norm = f.bgr[:, :, 1].astype(np.float32) / 255.0
            r_norm = f.bgr[:, :, 2].astype(np.float32) / 255.0

            r_means.append(float(np.mean(r_norm)))
            g_means.append(float(np.mean(g_norm)))
            b_means.append(float(np.mean(b_norm)))

            r_stds.append(float(np.std(r_norm)))
            g_stds.append(float(np.std(g_norm)))
            b_stds.append(float(np.std(b_norm)))

            if prev_gray is not None and prev_gray.shape == f.gray.shape:
                diff = float(np.mean(np.abs(f.gray.astype(np.float32) - prev_gray.astype(np.float32))) / 255.0)
            else:
                diff = 0.0
            deltas.append(diff)
            prev_gray = f.gray

        mean_r = float(np.mean(r_means))
        mean_g = float(np.mean(g_means))
        mean_b = float(np.mean(b_means))
        jitter = float(np.std(deltas)) if len(deltas) > 1 else 0.0

        rg_corr = float(np.corrcoef(r_means, g_means)[0, 1]) if len(r_means) > 2 and np.std(r_means) > 1e-5 and np.std(g_means) > 1e-5 else 0.0
        gb_corr = float(np.corrcoef(g_means, b_means)[0, 1]) if len(g_means) > 2 and np.std(g_means) > 1e-5 and np.std(b_means) > 1e-5 else 0.0

        # Flag anomalous jitter transitions (avoiding legitimate scene cuts)
        suspicious_intervals: List[SuspiciousTemporalInterval] = []
        if len(deltas) > 3:
            mean_d = float(np.mean(deltas))
            std_d = float(np.std(deltas))
            thresh = mean_d + 2.2 * std_d
            for idx, d_val in enumerate(deltas):
                if d_val > thresh and idx not in sample_res.scene_cut_indices and idx > 0:
                    start_ts = frames[idx - 1].timestamp_sec
                    end_ts = frames[idx].timestamp_sec
                    suspicious_intervals.append(
                        SuspiciousTemporalInterval(
                            start_timestamp=round(start_ts, 3),
                            end_timestamp=round(end_ts, 3),
                            frame_indices=[frames[idx - 1].frame_index, frames[idx].frame_index],
                            branch=self.analyzer_id,
                            measured_metric=f"Inter-frame delta Spike Delta={d_val:.4f}",
                            threshold_or_basis=f"Mean + 2.2*std ({thresh:.4f})",
                            explanation="Uncharacteristically abrupt intra-scene chromatic shift not matching camera cuts.",
                            confidence_semantics="Moderate Anomaly",
                            caveats="Could be caused by rapid camera auto-exposure or strobe lighting.",
                        )
                    )

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        summary_text = (
            f"Evaluated {len(frames)} frames across {sample_res.duration_sec:.2f}s. "
            f"Channel Means: R={mean_r*100:.1f}%, G={mean_g*100:.1f}%, B={mean_b*100:.1f}%. "
            f"Temporal jitter index: {jitter:.4f}. Found {len(suspicious_intervals)} chromatic anomalies."
        )

        return (
            BranchForensicResult(
                analyzer_id=self.analyzer_id,
                status=VideoAnalyzerStatus.COMPLETED,
                method=self.method,
                frames_analyzed=len(frames),
                timestamps_analyzed=timestamps,
                raw_metrics={
                    "mean_red": round(mean_r, 4),
                    "mean_green": round(mean_g, 4),
                    "mean_blue": round(mean_b, 4),
                    "rg_correlation": round(rg_corr, 4) if not np.isnan(rg_corr) else 0.0,
                    "gb_correlation": round(gb_corr, 4) if not np.isnan(gb_corr) else 0.0,
                    "temporal_jitter_index": round(jitter, 4),
                    "frame_deltas": [round(d, 4) for d in deltas],
                    "scene_cut_count": len(sample_res.scene_cut_indices),
                },
                score=round(min(1.0, jitter * 5.0), 4),
                score_semantics="Normalized Chromatic Jitter Index [0, 1]",
                runtime_ms=round(elapsed_ms, 2),
                warnings=[],
                limitations=[
                    "Cannot prove AI generation independently; lighting and cuts affect metrics.",
                    "Not clinical photoplethysmography (rPPG)."
                ],
                evidence_summary=summary_text,
            ),
            suspicious_intervals,
        )
