import logging
from typing import Tuple
from PIL import Image

from app.schemas.evidence import VideoForensicResult
from app.services.video_orchestrator import VideoForensicsOrchestrator
from app.services.video_sampler import VideoFrameSampler

logger = logging.getLogger(__name__)

def analyze_video_stream(
    video_bytes: bytes,
    filename: str = "evidence_video.mp4",
    sample_interval_sec: float = 0.5,
    max_samples: int = 32,
    preset: str = "fast",
) -> VideoForensicResult:
    """Main entrypoint for multi-layer video forensic analysis.
    
    Delegates to VideoForensicsOrchestrator while preserving exact function signature.
    """
    orchestrator = VideoForensicsOrchestrator(preset=preset)
    return orchestrator.analyze(video_bytes=video_bytes, filename=filename)

def extract_single_video_frame(
    video_bytes: bytes,
    timestamp_sec: float,
    filename: str = "evidence_video.mp4",
) -> Tuple[Image.Image, float, int]:
    """Extracts a single decoded frame at the specified timestamp as a PIL Image."""
    sampler = VideoFrameSampler(max_samples=1)
    res = sampler.sample_from_bytes(video_bytes, filename=filename)
    if not res.frames:
        raise ValueError(f"Could not extract frame from {filename}")
    
    # Pick frame closest to timestamp_sec
    closest = min(res.frames, key=lambda f: abs(f.timestamp_sec - timestamp_sec))
    pil_img = Image.fromarray(closest.rgb)
    return pil_img, closest.timestamp_sec, closest.frame_index
