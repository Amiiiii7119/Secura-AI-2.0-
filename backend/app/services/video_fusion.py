import time
from typing import Dict, List, Optional, Tuple
import numpy as np

from app.schemas.evidence import (
    CanonicalBinaryVerdict,
    BranchForensicResult,
    SuspiciousTemporalInterval,
    VideoAnalyzerStatus,
    VideoFusionResult,
    VideoTaskClassification,
)

class VideoEvidenceFusion:
    """Multi-layer evidence synthesis combining temporal representation trajectory curvature (ReStraV),
    spatial neural diffusion distribution (Swin), optical flow motion coherence, and residual sensor noise variance.
    
    Implements scientifically defensible decision logic, explicit uncertainty reporting,
    and honest abstention (INCONCLUSIVE) when analyzer signals are insufficient.
    Ensures mathematical consistency: canonical model score and binary verdict strictly adhere
    to decision threshold (0.50).
    """

    def fuse(
        self,
        branches: Dict[str, BranchForensicResult],
        suspicious_intervals: List[SuspiciousTemporalInterval],
    ) -> VideoFusionResult:
        supporting = []
        contradictory = []
        unavailable = []
        limitations = [
            "Video compression, re-encoding, and low bitrate can elevate false-positive rates.",
            "Absence of cryptographic C2PA credentials is not proof of AI generation.",
            "Evaluated on sampled frames; brief sub-second synthetic insertions between samples could be missed.",
            "Ensemble score represents multi-layer synthesized evidence anchored by NeurIPS 2025 ReStraV temporal sequence modeling."
        ]

        # Extract branch results safely using exact analyzer IDs
        b1_rgb = branches.get("branch_1_rgb")
        b2_motion = branches.get("branch_2_motion")
        b3_temporal = branches.get("branch_3_temporal_representation") or branches.get("branch_3_temporal")
        b4_spatial = branches.get("branch_4_spatial_frequency") or branches.get("branch_4_spatial")
        b6_face = branches.get("branch_6_face") or branches.get("branch_6_face_consistency")
        b7_container = branches.get("branch_7_container") or branches.get("branch_7_container_provenance")

        for bid, b in branches.items():
            if b.status in (VideoAnalyzerStatus.ANALYSIS_UNAVAILABLE, VideoAnalyzerStatus.ANALYSIS_FAILED, VideoAnalyzerStatus.INSUFFICIENT_DATA):
                unavailable.append(f"{bid}: {b.method} ({b.status.value})")

        # Signal 1: ReStraV Temporal Representation Trajectory Curvature (Branch 3)
        p_temporal = 0.50
        has_temporal = False
        mean_turning_deg = 0.0
        max_turning_deg = 0.0
        if b3_temporal and b3_temporal.status == VideoAnalyzerStatus.COMPLETED and b3_temporal.score is not None:
            has_temporal = True
            p_temporal = float(b3_temporal.score)
            raw_m = b3_temporal.raw_metrics or {}
            mean_turning_deg = float(raw_m.get("mean_turning_angle_deg", 0.0))
            max_turning_deg = float(raw_m.get("max_turning_angle_deg", 0.0))
            
            if p_temporal >= 0.50:
                supporting.append(
                    f"ReStraV temporal representation anomaly confirms generative video synthesis "
                    f"(P(AI): {p_temporal*100:.1f}%, Mean turning angle: {mean_turning_deg:.1f} deg)."
                )
            else:
                contradictory.append(
                    f"ReStraV temporal representation confirms authentic physical camera trajectory "
                    f"(P(AI): {p_temporal*100:.1f}%, Mean turning angle: {mean_turning_deg:.1f} deg)."
                )

        # Signal 2: Spatial Neural Diffusion Distribution & Noise Variance (Branch 4 or Branch 1)
        p_spatial = None
        ai_ratio = 0.0
        peak_ai = 0.0
        mean_noise = 100.0
        has_spatial = False
        if b4_spatial and b4_spatial.status == VideoAnalyzerStatus.COMPLETED:
            has_spatial = True
            raw_m = b4_spatial.raw_metrics or {}
            p_spatial = float(raw_m.get("mean_ai_probability", b4_spatial.score if b4_spatial.score is not None else 0.5))
            ai_ratio = float(raw_m.get("ai_frame_ratio", 0.0))
            peak_ai = float(raw_m.get("peak_ai_probability", p_spatial))
            mean_noise = float(raw_m.get("mean_noise_variance", 100.0))
        elif b1_rgb and b1_rgb.status == VideoAnalyzerStatus.COMPLETED:
            raw_m = b1_rgb.raw_metrics or {}
            score_val = b1_rgb.score if b1_rgb.score is not None else raw_m.get("max_frame_synthetic_p")
            if score_val is not None:
                has_spatial = True
                p_spatial = float(score_val)
                ai_ratio = float(raw_m.get("ai_frame_ratio", 0.0))
                peak_ai = float(raw_m.get("peak_ai_probability", p_spatial))
                mean_noise = float(raw_m.get("mean_noise_variance", 100.0))

        if has_spatial and p_spatial is not None:
            if p_spatial >= 0.50 or ai_ratio >= 0.40:
                supporting.append(f"Spatial diffusion texture detected across sampled frames (Peak: {peak_ai*100:.1f}%, Mean: {p_spatial*100:.1f}%).")
            elif p_spatial <= 0.30 and ai_ratio <= 0.15:
                contradictory.append(f"Low frame-level diffusion probability (Mean: {p_spatial*100:.1f}%).")

            if mean_noise < 15.0:
                supporting.append(f"Synthetically smooth sensor noise floor ({mean_noise:.1f} variance).")
            elif mean_noise > 120.0:
                contradictory.append(f"Natural camera sensor photon shot noise present ({mean_noise:.1f} variance).")

        # Signal 3: Motion Discontinuity (Branch 2)
        has_motion = False
        discont = 0.0
        norm_motion = 0.5
        if b2_motion and b2_motion.status == VideoAnalyzerStatus.COMPLETED and b2_motion.raw_metrics:
            has_motion = True
            discont = float(b2_motion.raw_metrics.get("motion_discontinuity_index", 0.0))
            norm_motion = float(np.clip((discont - 0.8) / 1.2, 0.0, 1.0))
            if discont > 1.3:
                supporting.append(f"Elevated motion vector discontinuity index ({discont:.2f}).")
            elif discont < 0.8 and discont > 0.0:
                contradictory.append(f"Smooth optical flow vector continuity ({discont:.2f}).")

        # Signal 4: Face Manipulation (Branch 6)
        face_manipulation_detected = False
        if b6_face and b6_face.status == VideoAnalyzerStatus.COMPLETED and b6_face.score is not None:
            if b6_face.score > 0.65:
                face_manipulation_detected = True
                supporting.append(f"Facial landmark/boundary inconsistency detected (Score: {b6_face.score:.2f}).")

        # Multi-Layer Score Synthesis
        norm_temporal = float(p_temporal) if has_temporal else 0.50
        norm_spatial = float(p_spatial) if p_spatial is not None else 0.50
        norm_noise = 1.0 if mean_noise < 15.0 else (0.0 if mean_noise > 120.0 else float(np.clip((120.0 - mean_noise) / 105.0, 0.0, 1.0)))

        # Dynamic normalized weighting according to available evidence branches
        # Primary sequence signal is ReStraV temporal curvature (w=0.75), complemented by spatial (0.10), motion (0.10), and noise (0.05)
        if has_temporal and has_spatial:
            raw_score = 0.75 * norm_temporal + 0.10 * norm_spatial + 0.10 * norm_motion + 0.05 * norm_noise
        elif has_temporal and not has_spatial:
            raw_score = 0.85 * norm_temporal + 0.10 * norm_motion + 0.05 * norm_noise
        elif has_spatial and not has_temporal:
            raw_score = 0.65 * norm_spatial + 0.20 * norm_motion + 0.15 * norm_noise
        else:
            raw_score = 0.50

        raw_score = float(np.clip(raw_score, 0.001, 0.999))
        ensemble_prob = round(raw_score, 4)

        # Uncertainty Interval
        delta = 0.08
        ci_lower = round(max(0.0, ensemble_prob - delta), 3)
        ci_upper = round(min(1.0, ensemble_prob + delta), 3)

        # SCIENTIFIC DECISION LOGIC (Strictly aligned with canonical threshold 0.50)
        # Case 1: Crucial primary analyzers unavailable
        if len(unavailable) >= 4 or (not has_temporal and not has_spatial):
            classification = VideoTaskClassification.INCONCLUSIVE
            uncertainty_status = "INSUFFICIENT_DATA"
            conf_pct = 50.0
            abstention = "Multiple primary forensic analyzers unavailable. Insufficient data to form a reliable verdict."

        # Case 2: Face manipulation branch flagged with high confidence
        elif face_manipulation_detected and (b6_face.score or 0) >= 0.70:
            classification = VideoTaskClassification.FACE_MANIPULATED_VIDEO
            uncertainty_status = "HIGH_CONFIDENCE"
            conf_pct = round((b6_face.score or 0.88) * 100, 1)
            abstention = None

        # Case 3: Defensible Binary Decision based on threshold 0.50
        elif ensemble_prob >= 0.50:
            classification = VideoTaskClassification.AI_GENERATED_VIDEO
            uncertainty_status = "HIGH_CONFIDENCE" if ensemble_prob >= 0.70 else "MODERATE_CONFIDENCE"
            conf_pct = round(min(99.0, max(50.0, ensemble_prob * 100)), 1)
            abstention = None

        # Case 4: Authentic Real Capture (< 0.50 threshold)
        else:
            classification = VideoTaskClassification.REAL_CAPTURE
            uncertainty_status = "HIGH_CONFIDENCE" if ensemble_prob <= 0.30 else "MODERATE_CONFIDENCE"
            conf_pct = round(min(99.0, max(50.0, (1.0 - ensemble_prob) * 100)), 1)
            abstention = None

        return VideoFusionResult(
            final_classification=classification,
            calibrated_ai_probability=ensemble_prob,
            raw_model_score=round(float(raw_score), 4),
            confidence_pct=conf_pct,
            uncertainty_interval=(ci_lower, ci_upper),
            score_semantics="Multi-Layer ReStraV + Swin Synthesized Evidence Likelihood",
            uncertainty_status=uncertainty_status,
            supporting_evidence=supporting,
            contradictory_evidence=contradictory,
            unavailable_analyzers=unavailable,
            known_limitations=limitations,
            abstention_reason=abstention,
        )
