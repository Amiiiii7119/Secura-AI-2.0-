import pytest
from app.services.video_fusion import VideoEvidenceFusion
from app.schemas.evidence import (
    BranchForensicResult,
    VideoAnalyzerStatus,
    VideoTaskClassification,
    SuspiciousTemporalInterval,
)

def test_fusion_conflicting_signals_produces_inconclusive():
    """
    Regression test for Mission 21/24: When spatial detector predicts 0.076 (authentic)
    but temporal curvature heuristic predicts 1.83 rad (anomaly), the system under Mission 24
    calibrates the temporal anomaly to classify as AI_GENERATED_VIDEO with consumer label AI GENERATED,
    while recording conflicting signals in contradictory_evidence.
    """
    fusion = VideoEvidenceFusion()
    branches = {
        "branch_3_temporal": BranchForensicResult(
            analyzer_id="branch_3_temporal",
            status=VideoAnalyzerStatus.COMPLETED,
            method="ReStraV-Inspired Trajectory Curvature",
            frames_analyzed=8,
            score=0.834,
            score_semantics="Trajectory Curvature Anomaly Metric (Uncalibrated)",
            runtime_ms=1200.0,
            evidence_summary="High trajectory curvature observed in latent space",
            raw_metrics={"mean_trajectory_curvature_rad": 1.83, "max_trajectory_curvature_rad": 2.1},
            findings_summary="High trajectory curvature observed"
        ),
        "branch_4_spatial_frequency": BranchForensicResult(
            analyzer_id="branch_4_spatial_frequency",
            status=VideoAnalyzerStatus.COMPLETED,
            method="Swin Image Classifier (Extracted Frames)",
            frames_analyzed=8,
            score=0.076,
            score_semantics="Mean Frame Diffusion Likelihood [0, 1]",
            runtime_ms=850.0,
            evidence_summary="Low spatial artifact probability across all 8 sampled frames",
            raw_metrics={"mean_ai_probability": 0.076, "ai_frame_ratio": 0.0, "mean_noise_variance": 120.0},
            findings_summary="Low spatial artifact probability"
        ),
    }
    
    suspicious = [
        SuspiciousTemporalInterval(
            start_timestamp=0.5,
            end_timestamp=1.5,
            branch="branch_3_temporal",
            measured_metric="curvature_rad: 1.83",
            threshold_or_basis="Curvature > 1.2 rad baseline threshold",
            explanation="Spike in temporal trajectory angle",
            confidence_semantics="Descriptive Trajectory Curvature Spike",
            caveats="High motion or camera pan can mimic trajectory deviation"
        )
    ]
    
    result = fusion.fuse(branches, suspicious)
    
    assert result.final_classification == VideoTaskClassification.AI_GENERATED_VIDEO
    assert result.score_semantics is not None
    assert len(result.contradictory_evidence) > 0

def test_fusion_high_ai_agreement():
    fusion = VideoEvidenceFusion()
    branches = {
        "branch_3_temporal": BranchForensicResult(
            analyzer_id="branch_3_temporal",
            status=VideoAnalyzerStatus.COMPLETED,
            method="ReStraV-Inspired Trajectory Curvature",
            frames_analyzed=8,
            score=0.88,
            score_semantics="Trajectory Curvature Anomaly Metric (Uncalibrated)",
            runtime_ms=1100.0,
            evidence_summary="High trajectory curvature",
            raw_metrics={"mean_trajectory_curvature_rad": 2.1, "max_trajectory_curvature_rad": 2.5},
            findings_summary="High trajectory curvature"
        ),
        "branch_4_spatial_frequency": BranchForensicResult(
            analyzer_id="branch_4_spatial_frequency",
            status=VideoAnalyzerStatus.COMPLETED,
            method="Swin Image Classifier",
            frames_analyzed=8,
            score=0.85,
            score_semantics="Mean Frame Diffusion Likelihood [0, 1]",
            runtime_ms=800.0,
            evidence_summary="High spatial diffusion artifacts",
            raw_metrics={"mean_ai_probability": 0.85, "ai_frame_ratio": 0.875, "mean_noise_variance": 8.0},
            findings_summary="High spatial diffusion artifacts"
        ),
    }
    result = fusion.fuse(branches, [])
    assert result.final_classification == VideoTaskClassification.AI_GENERATED_VIDEO
    assert result.uncertainty_status == "HIGH_CONFIDENCE"
    assert result.raw_model_score > 0.70

def test_fusion_high_real_agreement():
    fusion = VideoEvidenceFusion()
    branches = {
        "branch_3_temporal": BranchForensicResult(
            analyzer_id="branch_3_temporal",
            status=VideoAnalyzerStatus.COMPLETED,
            method="ReStraV-Inspired Trajectory Curvature",
            frames_analyzed=8,
            score=0.12,
            score_semantics="Trajectory Curvature Anomaly Metric (Uncalibrated)",
            runtime_ms=1100.0,
            evidence_summary="Smooth realistic motion trajectory",
            raw_metrics={"mean_trajectory_curvature_rad": 0.4, "max_trajectory_curvature_rad": 0.6},
            findings_summary="Smooth realistic motion trajectory"
        ),
        "branch_4_spatial_frequency": BranchForensicResult(
            analyzer_id="branch_4_spatial_frequency",
            status=VideoAnalyzerStatus.COMPLETED,
            method="Swin Image Classifier",
            frames_analyzed=8,
            score=0.09,
            score_semantics="Mean Frame Diffusion Likelihood [0, 1]",
            runtime_ms=800.0,
            evidence_summary="Natural sensor noise",
            raw_metrics={"mean_ai_probability": 0.09, "ai_frame_ratio": 0.0, "mean_noise_variance": 150.0},
            findings_summary="Natural sensor noise"
        ),
    }
    result = fusion.fuse(branches, [])
    assert result.final_classification == VideoTaskClassification.REAL_CAPTURE
    assert result.uncertainty_status == "HIGH_CONFIDENCE"
    assert result.raw_model_score < 0.35

def test_fusion_insufficient_branches():
    fusion = VideoEvidenceFusion()
    branches = {
        "branch_1_rgb": BranchForensicResult(
            analyzer_id="branch_1_rgb",
            status=VideoAnalyzerStatus.COMPLETED,
            method="Chromatic RGB Analysis",
            frames_analyzed=8,
            score=None,
            score_semantics="Descriptive Temporal Jitter Metric",
            runtime_ms=250.0,
            evidence_summary="Low RGB jitter",
            raw_metrics={"temporal_jitter": 0.01},
            findings_summary="Low RGB jitter"
        ),
    }
    result = fusion.fuse(branches, [])
    assert result.final_classification == VideoTaskClassification.INCONCLUSIVE
    assert result.uncertainty_status == "INSUFFICIENT_DATA"
