import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, r"D:\SecuraAI2\backend")

from app.services.video_orchestrator import VideoForensicsOrchestrator
from app.services.video_sampler import VideoFrameSampler
from app.services.ai_image_detector import AIImageDetectorService

AI_VIDEO_PATH = Path(r"D:\SecuraAI2\data\benchmark_videos\ai\8328099-uhd_2160_3840_25fps.mp4")
REAL_VIDEO_PATH = Path(r"D:\SecuraAI2\data\benchmark_videos\real\istockphoto-1282573958-640_adpp_is.mp4")

@pytest.fixture(scope="module")
def orchestrator():
    return VideoForensicsOrchestrator()

def test_user_ai_video_detected_as_ai(orchestrator):
    assert AI_VIDEO_PATH.exists(), f"Missing benchmark AI video: {AI_VIDEO_PATH}"
    video_bytes = AI_VIDEO_PATH.read_bytes()
    res = orchestrator.analyze(video_bytes, filename=AI_VIDEO_PATH.name)
    
    cv = res.canonical_verdict
    assert cv.predicted_label == "AI_GENERATED", f"Expected AI_GENERATED, got {cv.predicted_label}"
    assert cv.model_score >= 0.50, f"Expected score >= 0.50, got {cv.model_score}"
    
    b3 = res.branches.get("branch_3_temporal_representation") or res.branches.get("branch_3_temporal")
    assert b3 is not None, "Branch 3 missing from result branches"
    assert b3.status.value.lower() == "completed", f"Branch 3 status: {b3.status.value}"
    assert b3.score is not None and b3.score >= 0.50, f"Expected ReStraV P(AI) >= 0.50, got {b3.score}"

def test_user_real_video_detected_as_real(orchestrator):
    assert REAL_VIDEO_PATH.exists(), f"Missing benchmark Real video: {REAL_VIDEO_PATH}"
    video_bytes = REAL_VIDEO_PATH.read_bytes()
    res = orchestrator.analyze(video_bytes, filename=REAL_VIDEO_PATH.name)
    
    cv = res.canonical_verdict
    assert cv.predicted_label == "NOT_AI_GENERATED", f"Expected NOT_AI_GENERATED, got {cv.predicted_label}"
    assert cv.model_score < 0.50, f"Expected score < 0.50, got {cv.model_score}"
    
    b3 = res.branches.get("branch_3_temporal_representation") or res.branches.get("branch_3_temporal")
    assert b3 is not None, "Branch 3 missing from result branches"
    assert b3.status.value.lower() == "completed", f"Branch 3 status: {b3.status.value}"
    assert b3.score is not None and b3.score < 0.50, f"Expected ReStraV P(AI) < 0.50, got {b3.score}"

def test_consecutive_frame_sampler():
    assert REAL_VIDEO_PATH.exists()
    sampler = VideoFrameSampler()
    sample_res = sampler.sample_from_bytes(REAL_VIDEO_PATH.read_bytes(), filename=REAL_VIDEO_PATH.name)
    
    assert hasattr(sample_res, "consecutive_frames"), "SamplingResult must contain consecutive_frames"
    assert len(sample_res.consecutive_frames) >= 8, f"Expected at least 8 consecutive frames, got {len(sample_res.consecutive_frames)}"
    
    # Check that consecutive frames are strictly consecutive (step=1)
    indices = [f.frame_index for f in sample_res.consecutive_frames]
    for i in range(len(indices) - 1):
        assert indices[i+1] == indices[i] + 1, f"Frame indices not consecutive: {indices[i]} -> {indices[i+1]}"

def test_no_singleton_state_mutation():
    detector = AIImageDetectorService()
    # Ensure predict_frame_swin exists and can be called without calling switch_head
    assert hasattr(detector, "predict_frame_swin"), "AIImageDetectorService must expose predict_frame_swin"
    # Ensure switch_head is not called internally by checking active_head stability
    initial_head = detector.active_head
    import numpy as np
    dummy_bgr = np.zeros((224, 224, 3), dtype=np.uint8)
    p_swin = detector.predict_frame_swin(dummy_bgr)
    assert isinstance(p_swin, float)
    assert 0.0 <= p_swin <= 1.0
    assert detector.active_head == initial_head, f"Active head mutated: {initial_head} -> {detector.active_head}"
