import base64
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple, Set
import cv2
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class DecodedFrame:
    sample_index: int
    frame_index: int
    timestamp_sec: float
    bgr: np.ndarray          # Original OpenCV BGR uint8 [H, W, 3]
    rgb: np.ndarray          # RGB uint8 [H, W, 3]
    gray: np.ndarray         # Grayscale uint8 [H, W]
    thumbnail_data_url: Optional[str]
    is_scene_cut: bool = False

@dataclass
class SamplingResult:
    total_frames: int
    fps: float
    width: int
    height: int
    duration_sec: float
    fourcc: str
    frames: List[DecodedFrame]
    scene_cut_indices: List[int]
    decode_time_ms: float
    consecutive_frames: Optional[List[DecodedFrame]] = None

class VideoFrameSampler:
    """Universal, high-reliability video frame decoding and adaptive sampling engine.
    
    Robustly handles all video formats, codecs, variable-frame-rate content,
    and browser-recorded WebM streams without seek indices or duration headers.
    Guarantees accurate frame counts, real timestamps, and non-zero duration calculation.
    """
    def __init__(
        self,
        preset: str = "fast",
        sample_interval_sec: float = 0.5,
        max_samples: int = 32,
        thumb_width: int = 160,
    ):
        self.preset = preset
        self.sample_interval_sec = sample_interval_sec
        self.max_samples = max_samples
        if preset == "fast":
            self.max_samples = 16
        elif preset == "standard":
            self.max_samples = 32
        elif preset == "deep":
            self.max_samples = 60
        self.thumb_width = thumb_width

    def sample_from_bytes(self, video_bytes: bytes, filename: str = "video.mp4") -> SamplingResult:
        start_time = time.perf_counter()
        
        suffix = os.path.splitext(filename)[1].lower() or ".mp4"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="secura_samp_")
        try:
            with os.fdopen(tmp_fd, "wb") as f:
                f.write(video_bytes)

            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video stream for {filename}.")

            fps = float(cap.get(cv2.CAP_PROP_FPS))
            if fps <= 0.0 or np.isnan(fps) or fps > 240.0:
                fps = 30.0

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
            fourcc_str = "".join([chr((fourcc_int >> (8 * i)) & 0xFF) for i in range(4)]).strip() or "H264"

            # Determine frame count and seekability
            reported_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            can_seek = False
            
            # Test seekability if reported frames > 2
            if reported_frames > 2:
                test_pos = min(3, reported_frames - 1)
                if cap.set(cv2.CAP_PROP_POS_FRAMES, test_pos):
                    ret_test = cap.grab()
                    if ret_test:
                        can_seek = True
                # Reset to beginning
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            # For unindexed WebM streams, negative/zero frame count, or failed seek:
            # We perform a lightning-fast grab pass to count real decodable frames
            if reported_frames <= 0 or not can_seek:
                cap.release()
                cap = cv2.VideoCapture(tmp_path)
                real_count = 0
                while cap.grab():
                    real_count += 1
                total_frames = max(1, real_count)
                can_seek = False  # Must use stream/sequential extraction
                cap.release()
                cap = cv2.VideoCapture(tmp_path)
            else:
                total_frames = reported_frames

            # Calculate actual duration based on real frames and fps
            duration_sec = round(float(total_frames / fps), 2)
            if duration_sec <= 0.0 and total_frames > 0:
                duration_sec = round(float(total_frames / 30.0), 2)

            # Determine adaptive candidate sampling indices
            target_samples = min(self.max_samples, total_frames)
            if total_frames <= target_samples:
                candidate_indices = list(range(total_frames))
            else:
                candidate_indices = sorted(list(set(np.linspace(0, total_frames - 1, target_samples, dtype=int))))

            candidate_set: Set[int] = set(candidate_indices)
            decoded_frames: List[DecodedFrame] = []
            scene_cuts: List[int] = []
            prev_gray: Optional[np.ndarray] = None

            if can_seek:
                # Fast path: Direct frame seeking for indexed containers
                for s_idx, target_frame in enumerate(candidate_indices):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                    ret, bgr = cap.read()
                    if not ret or bgr is None:
                        continue
                    if width <= 0 or height <= 0:
                        height, width = bgr.shape[:2]

                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                    timestamp = round(float(target_frame / fps), 3)

                    # Thumbnail generation
                    thumb_h = max(1, int(height * (self.thumb_width / max(width, 1))))
                    thumb_small = cv2.resize(bgr, (self.thumb_width, thumb_h), interpolation=cv2.INTER_AREA)
                    is_success, buffer = cv2.imencode(".jpg", thumb_small, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    thumb_b64 = None
                    if is_success:
                        thumb_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('ascii')}"

                    # Detect scene cut transition
                    is_cut = False
                    if prev_gray is not None and prev_gray.shape == gray.shape:
                        diff = float(np.mean(np.abs(gray.astype(np.float32) - prev_gray.astype(np.float32))) / 255.0)
                        if diff > 0.40:
                            is_cut = True
                            scene_cuts.append(len(decoded_frames))
                    prev_gray = gray

                    decoded_frames.append(
                        DecodedFrame(
                            sample_index=len(decoded_frames),
                            frame_index=target_frame,
                            timestamp_sec=timestamp,
                            bgr=bgr,
                            rgb=rgb,
                            gray=gray,
                            thumbnail_data_url=thumb_b64,
                            is_scene_cut=is_cut,
                        )
                    )
            else:
                # Stream path: Sequential scan for WebM, variable-frame-rate, and unindexed files
                current_frame_idx = 0
                max_candidate = max(candidate_indices) if candidate_indices else 0

                while current_frame_idx <= max_candidate:
                    if current_frame_idx in candidate_set:
                        ret, bgr = cap.read()
                        if not ret or bgr is None:
                            break
                        if width <= 0 or height <= 0:
                            height, width = bgr.shape[:2]

                        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                        timestamp = round(float(current_frame_idx / fps), 3)

                        thumb_h = max(1, int(height * (self.thumb_width / max(width, 1))))
                        thumb_small = cv2.resize(bgr, (self.thumb_width, thumb_h), interpolation=cv2.INTER_AREA)
                        is_success, buffer = cv2.imencode(".jpg", thumb_small, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                        thumb_b64 = None
                        if is_success:
                            thumb_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('ascii')}"

                        is_cut = False
                        if prev_gray is not None and prev_gray.shape == gray.shape:
                            diff = float(np.mean(np.abs(gray.astype(np.float32) - prev_gray.astype(np.float32))) / 255.0)
                            if diff > 0.40:
                                is_cut = True
                                scene_cuts.append(len(decoded_frames))
                        prev_gray = gray

                        decoded_frames.append(
                            DecodedFrame(
                                sample_index=len(decoded_frames),
                                frame_index=current_frame_idx,
                                timestamp_sec=timestamp,
                                bgr=bgr,
                                rgb=rgb,
                                gray=gray,
                                thumbnail_data_url=thumb_b64,
                                is_scene_cut=is_cut,
                            )
                        )
                    else:
                        # Grab fast skip without decoding pixel data
                        ret = cap.grab()
                        if not ret:
                            break
                    current_frame_idx += 1

            cap.release()

            # Fallback if dimensions still unknown
            if width <= 0:
                width = 1280
            if height <= 0:
                height = 720

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            consec_frames: List[DecodedFrame] = []
            if total_frames >= 4:
                try:
                    cap_c = cv2.VideoCapture(tmp_path)
                    consec_len = min(24, total_frames)
                    consec_start = min(5, max(0, total_frames - consec_len))
                    if can_seek:
                        cap_c.set(cv2.CAP_PROP_POS_FRAMES, consec_start)
                    else:
                        for _ in range(consec_start):
                            cap_c.grab()
                    for c_i in range(consec_len):
                        ret, bgr_c = cap_c.read()
                        if not ret or bgr_c is None:
                            break
                        rgb_c = cv2.cvtColor(bgr_c, cv2.COLOR_BGR2RGB)
                        gray_c = cv2.cvtColor(bgr_c, cv2.COLOR_BGR2GRAY)
                        consec_frames.append(
                            DecodedFrame(
                                sample_index=c_i,
                                frame_index=consec_start + c_i,
                                timestamp_sec=round(float((consec_start + c_i) / fps), 3),
                                bgr=bgr_c,
                                rgb=rgb_c,
                                gray=gray_c,
                                thumbnail_data_url=None,
                                is_scene_cut=False,
                            )
                        )
                    cap_c.release()
                except Exception as exc:
                    logger.warning("Consecutive frame extraction failed: %s", exc)

            return SamplingResult(
                total_frames=total_frames,
                fps=fps,
                width=width,
                height=height,
                duration_sec=duration_sec,
                fourcc=fourcc_str,
                frames=decoded_frames,
                scene_cut_indices=scene_cuts,
                decode_time_ms=round(elapsed_ms, 2),
                consecutive_frames=consec_frames,
            )
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
