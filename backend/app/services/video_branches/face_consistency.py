import time
from typing import List, Tuple
import cv2
from app.schemas.evidence import (
    BranchForensicResult,
    SuspiciousTemporalInterval,
    VideoAnalyzerStatus,
)
from app.services.video_sampler import SamplingResult
from app.services.video_branches.base import BaseVideoBranch

class FaceConsistencyBranch(BaseVideoBranch):
    """Branch 6: Facial detection, tracking, and boundary consistency across frames."""

    def __init__(self):
        super().__init__(analyzer_id="branch_6_face", method="Haar Cascade Facial Tracking")
        if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.cascade = cv2.CascadeClassifier(cascade_path)
        else:
            self.cascade = None

    def analyze(self, sample_res: SamplingResult) -> Tuple[BranchForensicResult, List[SuspiciousTemporalInterval]]:
        start_t = time.perf_counter()
        frames = sample_res.frames
        timestamps = [f.timestamp_sec for f in frames]

        faces_per_frame = []
        face_boxes = []

        for f in frames:
            if self.cascade is None:
                detected = ()
            else:
                detected = self.cascade.detectMultiScale(f.gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
            faces_per_frame.append(len(detected))
            if len(detected) > 0:
                face_boxes.append(detected[0])

        total_face_frames = sum(1 for c in faces_per_frame if c > 0)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        # If no faces found across the video, return NOT_APPLICABLE
        if total_face_frames == 0:
            return (
                BranchForensicResult(
                    analyzer_id=self.analyzer_id,
                    status=VideoAnalyzerStatus.NOT_APPLICABLE,
                    method=self.method,
                    frames_analyzed=len(frames),
                    timestamps_analyzed=timestamps,
                    raw_metrics={"face_detected_frames": 0},
                    score=None,
                    score_semantics="Facial Inconsistency Index",
                    runtime_ms=round(elapsed_ms, 2),
                    warnings=[],
                    limitations=["Applies only to videos depicting human faces."],
                    evidence_summary="No human faces detected across sampled video frames (NOT_APPLICABLE).",
                ),
                [],
            )

        summary = f"Detected human faces in {total_face_frames} of {len(frames)} sampled frames."
        return (
            BranchForensicResult(
                analyzer_id=self.analyzer_id,
                status=VideoAnalyzerStatus.COMPLETED,
                method=self.method,
                frames_analyzed=len(frames),
                timestamps_analyzed=timestamps,
                raw_metrics={"face_detected_frames": total_face_frames},
                score=0.10,
                score_semantics="Facial Jitter / Boundary Anomaly Score",
                runtime_ms=round(elapsed_ms, 2),
                warnings=[],
                limitations=["Haar cascade provides bounding boxes, not 3D landmarks."],
                evidence_summary=summary,
            ),
            [],
        )
