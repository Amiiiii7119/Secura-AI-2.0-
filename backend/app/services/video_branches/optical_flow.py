import time
from typing import List, Tuple
import cv2
import numpy as np
from app.schemas.evidence import (
    BranchForensicResult,
    SuspiciousTemporalInterval,
    VideoAnalyzerStatus,
)
from app.services.video_sampler import SamplingResult
from app.services.video_branches.base import BaseVideoBranch

class OpticalFlowBranch(BaseVideoBranch):
    """Branch 2: OpenCV Farneback dense optical flow, motion consistency, and discontinuity detection."""

    def __init__(self):
        super().__init__(analyzer_id="branch_2_motion", method="OpenCV Farneback Dense Optical Flow")

    def analyze(self, sample_res: SamplingResult) -> Tuple[BranchForensicResult, List[SuspiciousTemporalInterval]]:
        start_t = time.perf_counter()
        frames = sample_res.frames
        timestamps = [f.timestamp_sec for f in frames]

        if len(frames) < 2:
            return (
                BranchForensicResult(
                    analyzer_id=self.analyzer_id,
                    status=VideoAnalyzerStatus.INSUFFICIENT_DATA,
                    method=self.method,
                    frames_analyzed=len(frames),
                    timestamps_analyzed=timestamps,
                    raw_metrics={},
                    score=None,
                    score_semantics="Motion Discontinuity Index",
                    runtime_ms=round((time.perf_counter() - start_t) * 1000.0, 2),
                    warnings=["At least 2 frames required for optical flow."],
                    limitations=["Cannot compute motion vectors on single-frame video."],
                    evidence_summary="Insufficient frames for optical flow motion analysis.",
                ),
                [],
            )

        flow_magnitudes = []
        direction_stds = []
        discontinuities = []
        suspicious_intervals: List[SuspiciousTemporalInterval] = []

        prev_gray_scaled = None
        target_w, target_h = 320, 180

        for idx, f in enumerate(frames):
            gray_scaled = cv2.resize(f.gray, (target_w, target_h), interpolation=cv2.INTER_AREA)

            if prev_gray_scaled is not None:
                # Dense Farneback flow on downscaled resolution for high performance
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray_scaled,
                    gray_scaled,
                    None,
                    pyr_scale=0.5,
                    levels=3,
                    winsize=15,
                    iterations=3,
                    poly_n=5,
                    poly_sigma=1.2,
                    flags=0,
                )
                u = flow[..., 0]
                v = flow[..., 1]
                mag, ang = cv2.cartToPolar(u, v)

                mean_mag = float(np.mean(mag))
                dir_std = float(np.std(ang))

                flow_magnitudes.append(mean_mag)
                direction_stds.append(dir_std)

                # Compute motion discontinuity against preceding flow
                if len(flow_magnitudes) > 1:
                    mag_diff = abs(mean_mag - flow_magnitudes[-2])
                    discontinuities.append(mag_diff)
                    # Detect motion discontinuity if not a camera scene cut
                    if mag_diff > 4.5 and idx not in sample_res.scene_cut_indices:
                        suspicious_intervals.append(
                            SuspiciousTemporalInterval(
                                start_timestamp=round(frames[idx - 1].timestamp_sec, 3),
                                end_timestamp=round(f.timestamp_sec, 3),
                                frame_indices=[frames[idx - 1].frame_index, f.frame_index],
                                branch=self.analyzer_id,
                                measured_metric=f"Flow Magnitude Discontinuity Delta={mag_diff:.2f}",
                                threshold_or_basis="Threshold > 4.5 px/sample",
                                explanation="Unnatural motion velocity jump detected between adjacent frames.",
                                confidence_semantics="Moderate Motion Anomaly",
                                caveats="Can occur in fast handheld camera whips or action sequences.",
                            )
                        )
                else:
                    discontinuities.append(0.0)

            prev_gray_scaled = gray_scaled

        avg_mag = float(np.mean(flow_magnitudes)) if flow_magnitudes else 0.0
        avg_dir_std = float(np.mean(direction_stds)) if direction_stds else 0.0
        motion_irregularity = float(np.std(discontinuities)) if len(discontinuities) > 1 else 0.0

        # Score: motion irregularity normalized
        motion_score = round(min(1.0, max(0.0, motion_irregularity / 5.0)), 4)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        summary = (
            f"Dense optical flow tracked across {len(frames)-1} frame transitions. "
            f"Mean motion magnitude: {avg_mag:.2f} px. Mean direction entropy: {avg_dir_std:.2f} rad. "
            f"Motion discontinuity index: {motion_irregularity:.4f}."
        )

        return (
            BranchForensicResult(
                analyzer_id=self.analyzer_id,
                status=VideoAnalyzerStatus.COMPLETED,
                method=self.method,
                frames_analyzed=len(frames),
                timestamps_analyzed=timestamps,
                raw_metrics={
                    "mean_motion_magnitude": round(avg_mag, 3),
                    "direction_std_rad": round(avg_dir_std, 3),
                    "motion_discontinuity_index": round(motion_irregularity, 4),
                    "discontinuity_values": [round(d, 3) for d in discontinuities],
                },
                score=motion_score,
                score_semantics="Motion Irregularity Index [0, 1]",
                runtime_ms=round(elapsed_ms, 2),
                warnings=[],
                limitations=[
                    "Does not alone prove AI generation; real handheld video can be erratic.",
                    "Scene cuts are masked to avoid false positives."
                ],
                evidence_summary=summary,
            ),
            suspicious_intervals,
        )
