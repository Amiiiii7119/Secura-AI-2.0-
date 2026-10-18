import io
import pytest
from httpx import ASGITransport, AsyncClient
from pathlib import Path
from app.main import app

SAMPLE_VIDEO_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_test_video.mp4"


@pytest.mark.asyncio
async def test_analyze_video_endpoint():
    """Verify POST /api/v1/analyze/video decodes and analyzes video stream."""
    assert SAMPLE_VIDEO_PATH.exists(), "Sample test video fixture must exist"
    video_bytes = SAMPLE_VIDEO_PATH.read_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("sample_test_video.mp4", video_bytes, "video/mp4")}
        response = await client.post("/api/v1/analyze/video", files=files)

    assert response.status_code == 200
    data = response.json()

    assert "video_metadata" in data
    assert data["video_metadata"]["duration_sec"] > 0
    assert data["video_metadata"]["total_frames"] == 50
    assert "sampled_frames" in data
    assert len(data["sampled_frames"]) > 0

    first_sample = data["sampled_frames"][0]
    assert "r_mean" in first_sample
    assert "g_mean" in first_sample
    assert "b_mean" in first_sample
    assert "thumbnail_data_url" in first_sample

    assert "rgb_summary" in data
    assert "mean_red" in data["rgb_summary"]
    assert "mean_green" in data["rgb_summary"]
    assert "mean_blue" in data["rgb_summary"]
    assert "temporal_jitter_index" in data["rgb_summary"]


@pytest.mark.asyncio
async def test_analyze_video_frame_endpoint():
    """Verify POST /api/v1/analyze/video/frame extracts and runs forensics on a single frame."""
    assert SAMPLE_VIDEO_PATH.exists()
    video_bytes = SAMPLE_VIDEO_PATH.read_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("sample_test_video.mp4", video_bytes, "video/mp4")}
        data = {"timestamp_sec": "0.5"}
        response = await client.post("/api/v1/analyze/video/frame", files=files, data=data)

    assert response.status_code == 200
    res = response.json()
    assert "image_validation" in res
    assert res["image_validation"]["is_valid"] is True
    assert "ela_forensics" in res
    assert "ai_detection" in res
