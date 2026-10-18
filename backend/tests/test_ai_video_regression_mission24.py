import os
from pathlib import Path
import pytest
from app.services.video_orchestrator import VideoForensicsOrchestrator
from app.schemas.evidence import CanonicalBinaryVerdict

VIDEO_PATH = Path(r"C:\Users\ammur\Downloads\8328099-uhd_2160_3840_25fps.mp4")

@pytest.mark.skipif(not VIDEO_PATH.exists(), reason="Regression AI video fixture not present on local machine")
def test_mission24_known_ai_video_regression():
    """
    Mission 24 Regression Test:
    Ensures that 8328099-uhd_2160_3840_25fps.mp4 is correctly classified as AI GENERATED
    via real temporal representation curvature analysis rather than hardcoding.
    """
    video_bytes = VIDEO_PATH.read_bytes()
    assert len(video_bytes) > 10_000_000, "Expected full UHD video file"

    orchestrator = VideoForensicsOrchestrator()
    result = orchestrator.analyze(video_bytes=video_bytes, filename=VIDEO_PATH.name)

    # 1. Canonical Verdict Verification
    assert result.canonical_verdict is not None, "Canonical verdict must be present"
    assert result.canonical_verdict.predicted_label == "AI_GENERATED", (
        f"Expected AI_GENERATED, got {result.canonical_verdict.predicted_label}"
    )
    assert result.canonical_verdict.display_label == "AI GENERATED"
    assert result.canonical_verdict.decision_threshold == 0.50
    assert result.canonical_verdict.model_score > 0.50, f"Expected score > 0.50, got {result.canonical_verdict.model_score}"

    # 2. Duration Integrity Verification
    assert result.video_metadata.duration_sec > 10.0, (
        f"Expected duration > 10s, got {result.video_metadata.duration_sec}"
    )

    # 3. Model feature grounding (no hardcoded flags)
    assert result.branches is not None
    assert "branch_3_temporal" in result.branches
    b3 = result.branches["branch_3_temporal"]
    assert b3.score >= 0.50
    assert "temporal representation" in result.canonical_verdict.evidence_summary.lower()
