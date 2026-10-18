import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
import numpy as np

from app.schemas.evidence import (
    CanonicalBinaryVerdict,
    BranchForensicResult,
    RGBFrameSample,
    RGBSummary,
    SuspiciousTemporalInterval,
    VideoAIVerdict,
    VideoForensicResult,
    VideoMetadata,
    VideoTaskClassification,
)
from app.services.video_sampler import VideoFrameSampler, SamplingResult
from app.services.video_branches.rgb_chromatic import RGBChromaticBranch
from app.services.video_branches.optical_flow import OpticalFlowBranch
from app.services.video_branches.temporal_representation import TemporalRepresentationBranch
from app.services.video_branches.spatial_frequency import SpatialFrequencyBranch
from app.services.video_branches.container_provenance import ContainerProvenanceBranch
from app.services.video_branches.face_consistency import FaceConsistencyBranch
from app.services.video_fusion import VideoEvidenceFusion

logger = logging.getLogger(__name__)

class VideoForensicsOrchestrator:
    """Modular multi-layer video forensics orchestrator.
    
    Coordinates the shared frame sampler, independent branches, and evidence fusion.
    Maintains 100% backward compatibility with legacy consumers while delivering
    Mission 18 multi-layer forensic depth.
    """
    def __init__(self, preset: str = "fast"):
        self.sampler = VideoFrameSampler(preset=preset)
        self.branch_rgb = RGBChromaticBranch()
        self.branch_motion = OpticalFlowBranch()
        self.branch_temporal = TemporalRepresentationBranch()
        self.branch_spatial = SpatialFrequencyBranch()
        self.branch_container = ContainerProvenanceBranch()
        self.branch_face = FaceConsistencyBranch()
        self.fusion_engine = VideoEvidenceFusion()

    def analyze(self, video_bytes: bytes, filename: str = "video.mp4") -> VideoForensicResult:
        request_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc)
        runtime_breakdown: Dict[str, float] = {}

        # 1. Ephemeral Frame Decoding and Sampling
        sample_res = self.sampler.sample_from_bytes(video_bytes, filename=filename)
        runtime_breakdown["decode_sampling_ms"] = sample_res.decode_time_ms

        branches: Dict[str, BranchForensicResult] = {}
        all_suspicious: List[SuspiciousTemporalInterval] = []

        # 2. Execute Branch 1: RGB & Chromatic
        b1_res, b1_flags = self.branch_rgb.analyze(sample_res)
        branches[b1_res.analyzer_id] = b1_res
        all_suspicious.extend(b1_flags)
        runtime_breakdown["branch_1_rgb_ms"] = b1_res.runtime_ms

        # 3. Execute Branch 2: Motion & Optical Flow
        b2_res, b2_flags = self.branch_motion.analyze(sample_res)
        branches[b2_res.analyzer_id] = b2_res
        all_suspicious.extend(b2_flags)
        runtime_breakdown["branch_2_motion_ms"] = b2_res.runtime_ms

        # 4. Execute Branch 3: Learned Temporal Representation (ReStraV)
        b3_res, b3_flags = self.branch_temporal.analyze(sample_res)
        branches[b3_res.analyzer_id] = b3_res
        branches["branch_3_temporal"] = b3_res  # Backward compatibility alias
        all_suspicious.extend(b3_flags)
        runtime_breakdown["branch_3_temporal_ms"] = b3_res.runtime_ms

        # 5. Execute Branch 4: Spatial & Frequency (Swin / Noise)
        b4_res, b4_flags = self.branch_spatial.analyze(sample_res)
        branches[b4_res.analyzer_id] = b4_res
        branches["branch_4_spatial"] = b4_res  # Backward compatibility alias
        all_suspicious.extend(b4_flags)
        runtime_breakdown["branch_4_spatial_ms"] = b4_res.runtime_ms

        # 6. Execute Branch 7: Container & Provenance
        b7_res, b7_flags = self.branch_container.analyze(sample_res)
        branches[b7_res.analyzer_id] = b7_res
        all_suspicious.extend(b7_flags)
        runtime_breakdown["branch_7_container_ms"] = b7_res.runtime_ms

        # 7. Execute Branch 6: Face Consistency (Optional)
        b6_res, b6_flags = self.branch_face.analyze(sample_res)
        branches[b6_res.analyzer_id] = b6_res
        all_suspicious.extend(b6_flags)
        runtime_breakdown["branch_6_face_ms"] = b6_res.runtime_ms

        # 8. Multi-Layer Evidence Fusion
        fusion_t = time.perf_counter()
        fusion_verdict = self.fusion_engine.fuse(branches, all_suspicious)
        runtime_breakdown["fusion_ms"] = round((time.perf_counter() - fusion_t) * 1000.0, 2)

        # 9. Assemble Legacy Models for Backward Compatibility
        metadata = VideoMetadata(
            filename=filename,
            width=sample_res.width,
            height=sample_res.height,
            fps=sample_res.fps,
            duration_sec=sample_res.duration_sec,
            total_frames=sample_res.total_frames,
            aspect_ratio=float(sample_res.width / max(sample_res.height, 1)),
            codec_fourcc=sample_res.fourcc,
        )

        b1_raw = b1_res.raw_metrics
        rgb_summary = RGBSummary(
            mean_red=b1_raw.get("mean_red", 0.5),
            mean_green=b1_raw.get("mean_green", 0.5),
            mean_blue=b1_raw.get("mean_blue", 0.5),
            rg_correlation=b1_raw.get("rg_correlation", 0.0),
            gb_correlation=b1_raw.get("gb_correlation", 0.0),
            temporal_jitter_index=b1_raw.get("temporal_jitter_index", 0.0),
            dominant_pulse_hz=None,
        )

        # Construct sampled_frames with per-frame probabilities from Branch 4 and deltas from Branch 1
        sampled_frames: List[RGBFrameSample] = []
        deltas = b1_raw.get("frame_deltas", [])
        spatial_probs = b4_res.raw_metrics.get("per_frame_ai_probs", [])
        noise_vars = b4_res.raw_metrics.get("per_frame_noise_vars", [])

        for idx, f in enumerate(sample_res.frames):
            b_norm = f.bgr[:, :, 0].astype(np.float32) / 255.0
            g_norm = f.bgr[:, :, 1].astype(np.float32) / 255.0
            r_norm = f.bgr[:, :, 2].astype(np.float32) / 255.0

            p_ai = spatial_probs[idx] if idx < len(spatial_probs) else None
            n_var = noise_vars[idx] if idx < len(noise_vars) else None
            d_prev = deltas[idx] if idx < len(deltas) else 0.0

            sampled_frames.append(
                RGBFrameSample(
                    sample_index=f.sample_index,
                    frame_index=f.frame_index,
                    timestamp_sec=f.timestamp_sec,
                    r_mean=float(np.mean(r_norm)),
                    g_mean=float(np.mean(g_norm)),
                    b_mean=float(np.mean(b_norm)),
                    r_std=float(np.std(r_norm)),
                    g_std=float(np.std(g_norm)),
                    b_std=float(np.std(b_norm)),
                    delta_prev_frame=d_prev,
                    thumbnail_data_url=f.thumbnail_data_url,
                    ai_probability=p_ai,
                    ai_class="AI_GENERATED" if (p_ai and p_ai > 0.5) else "LIKELY_REAL",
                    sensor_noise_variance=n_var,
                )
            )

        # Legacy VideoAIVerdict (Reconciled with unified multi-layer fusion score)
        if fusion_verdict.final_classification.value == "AI_GENERATED_VIDEO":
            legacy_decision = "AI_GENERATED_VIDEO"
        elif fusion_verdict.final_classification.value == "REAL_CAPTURE":
            legacy_decision = "AUTHENTIC_CAMERA_VIDEO"
        elif fusion_verdict.final_classification.value == "INCONCLUSIVE":
            legacy_decision = "INCONCLUSIVE"
        else:
            legacy_decision = "SUSPICIOUS_OR_HYBRID"

        ai_ratio = b4_res.raw_metrics.get("ai_frame_ratio", 0.0)
        peak_ai = b4_res.raw_metrics.get("peak_ai_probability", 0.0)
        syn_ai = fusion_verdict.calibrated_ai_probability if fusion_verdict.calibrated_ai_probability is not None else 0.5
        ai_count = sum(1 for p in spatial_probs if p > 0.5)

        legacy_verdict = VideoAIVerdict(
            decision=legacy_decision,
            confidence_pct=fusion_verdict.confidence_pct,
            mean_ai_probability=round(syn_ai, 4),
            peak_ai_probability=round(peak_ai, 4),
            ai_frame_ratio=round(ai_ratio, 4),
            ai_frames_detected=ai_count,
            total_frames_analyzed=len(sampled_frames),
            model_name="Secura Multi-Layer Forensic Engine (ReStraV + Swin + Farneback)",
            verdict_summary=f"Multi-layer determination: {fusion_verdict.final_classification.value} ({fusion_verdict.confidence_pct:.1f}% confidence, status: {fusion_verdict.uncertainty_status}).",
            evidence_breakdown=fusion_verdict.supporting_evidence + fusion_verdict.contradictory_evidence,
        )

        anomaly_ts = [s.start_timestamp for s in all_suspicious]

        notes = (
            f"Multi-Layer Forensics completed across {len(sampled_frames)} frames in {sample_res.duration_sec:.2f}s. "
            f"Executed 6 analytical branches: RGB chromatic, optical flow motion, ReStraV temporal curvature, "
            f"Swin spatial diffusion, container provenance, and facial tracking. "
            f"Flagged {len(all_suspicious)} suspicious temporal intervals."
        )

        # Mission 25: Canonical Consumer-First Binary Decision
        # Mathematical invariant: Model score is the canonical P(AI).
        # Predicted verdict is AI_GENERATED if and only if model_score >= decision_threshold (0.50).
        canonical_score = round(float(fusion_verdict.raw_model_score if fusion_verdict.raw_model_score is not None else fusion_verdict.calibrated_ai_probability), 4)
        decision_thresh = 0.50
        is_video_ai = canonical_score >= decision_thresh

        canonical_binary = CanonicalBinaryVerdict(
            predicted_label="AI_GENERATED" if is_video_ai else "NOT_AI_GENERATED",
            display_label="AI GENERATED" if is_video_ai else "NOT AI GENERATED",
            model_score=canonical_score,
            calibrated_probability=None,  # No false claim of calibration without empirical validation
            decision_threshold=decision_thresh,
            inference_time_ms=round(float(runtime_breakdown.get("total_ms", 0.0)), 2),
            model_version="2.0.0-video-fusion",
            evidence_summary=(
                fusion_verdict.supporting_evidence[0] if (is_video_ai and fusion_verdict.supporting_evidence)
                else (fusion_verdict.contradictory_evidence[0] if (not is_video_ai and fusion_verdict.contradictory_evidence)
                else ("Temporal trajectory curvature and latent transitions indicate generative video synthesis." if is_video_ai
                else "Temporal continuity and texture dynamics consistent with authentic camera capture."))
            ),
            warnings=fusion_verdict.unavailable_analyzers,
            methodology_note="Result synthesized from multi-layer spatial diffusion and temporal representation curvature. AI detectors may make mistakes."
        )

        return VideoForensicResult(
            request_id=request_id,
            timestamp_utc=now_utc,
            video_metadata=metadata,
            sampled_frames=sampled_frames,
            rgb_summary=rgb_summary,
            anomaly_timestamps=anomaly_ts,
            video_ai_verdict=legacy_verdict,
            analysis_notes=notes,
            branches=branches,
            suspicious_intervals=all_suspicious,
            fusion_verdict=fusion_verdict,
            canonical_verdict=canonical_binary,
            runtime_breakdown_ms=runtime_breakdown,
        )
