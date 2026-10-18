import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
import sys

sys.path.insert(0, r"D:\SecuraAI2\backend")
from app.main import app
from app.services.video_sampler import VideoFrameSampler
from app.services.video_orchestrator import VideoForensicsOrchestrator
from app.schemas.evidence import VideoTaskClassification

FIXTURE_DIR = Path(r"D:\SecuraAI2\backend\tests\fixtures")
SAMPLE_VIDEO = FIXTURE_DIR / "sample_test_video.mp4"

def test_sampler_uniform_and_scene_cuts():
    sampler = VideoFrameSampler()
    res = sampler.sample_from_bytes(SAMPLE_VIDEO.read_bytes(), filename="sample.mp4")
    assert len(res.frames) > 0
    assert res.total_frames >= len(res.frames)
    assert res.width > 0
    assert res.height > 0
    indices = [f.frame_index for f in res.frames]
    assert indices == sorted(indices)

def test_orchestrator_multi_branch_execution():
    orchestrator = VideoForensicsOrchestrator()
    video_bytes = SAMPLE_VIDEO.read_bytes()
    result = orchestrator.analyze(video_bytes, filename="sample.mp4")
    assert len(result.branches) >= 5
    branch_ids = list(result.branches.keys())
    assert "branch_1_rgb" in branch_ids
    assert "branch_2_motion" in branch_ids
    assert "branch_3_temporal" in branch_ids
    assert "branch_4_spatial_frequency" in branch_ids
    assert "branch_7_container" in branch_ids
    assert result.fusion_verdict is not None
    assert isinstance(result.fusion_verdict.final_classification, VideoTaskClassification)
    assert 0.0 <= result.fusion_verdict.raw_model_score <= 1.0

@pytest.mark.asyncio
async def test_full_video_pipeline_api():
    video_bytes = SAMPLE_VIDEO.read_bytes()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("sample.mp4", video_bytes, "video/mp4")}
        response = await client.post("/api/v1/analyze/video", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "branches" in data
        assert "fusion_verdict" in data
        assert "sampled_frames" in data
        assert "suspicious_intervals" in data
        assert len(data["branches"]) >= 5
