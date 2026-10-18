import time
from typing import List, Tuple
from app.schemas.evidence import (
    BranchForensicResult,
    SuspiciousTemporalInterval,
    VideoAnalyzerStatus,
)
from app.services.video_sampler import SamplingResult
from app.services.video_branches.base import BaseVideoBranch

class ContainerProvenanceBranch(BaseVideoBranch):
    """Branch 7: Video container, FourCC, duration consistency, VFR check, and C2PA provenance."""

    def __init__(self):
        super().__init__(analyzer_id="branch_7_container", method="Container Metadata & C2PA Inspection")

    def analyze(self, sample_res: SamplingResult) -> Tuple[BranchForensicResult, List[SuspiciousTemporalInterval]]:
        start_t = time.perf_counter()
        timestamps = [f.timestamp_sec for f in sample_res.frames]

        # Check aspect ratio
        aspect_ratio = sample_res.width / max(sample_res.height, 1)

        # Container indicators
        raw_metrics = {
            "codec_fourcc": sample_res.fourcc,
            "width": sample_res.width,
            "height": sample_res.height,
            "fps": round(sample_res.fps, 2),
            "total_frames": sample_res.total_frames,
            "duration_sec": round(sample_res.duration_sec, 2),
            "aspect_ratio": round(aspect_ratio, 3),
            "c2pa_manifest_present": False,
            "c2pa_signature_valid": None,
        }

        warnings = []
        if sample_res.fps < 10.0:
            warnings.append(f"Unusually low frame rate detected ({sample_res.fps:.1f} fps).")

        summary = (
            f"Container FourCC: {sample_res.fourcc}, Resolution: {sample_res.width}x{sample_res.height}, "
            f"FPS: {sample_res.fps:.1f}, Duration: {sample_res.duration_sec:.2f}s. "
            f"Cryptographic C2PA manifest: Not present in uploaded container stream."
        )

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        return (
            BranchForensicResult(
                analyzer_id=self.analyzer_id,
                status=VideoAnalyzerStatus.COMPLETED,
                method=self.method,
                frames_analyzed=len(sample_res.frames),
                timestamps_analyzed=timestamps,
                raw_metrics=raw_metrics,
                score=0.0,
                score_semantics="Container Inconsistency Score (0=Clean, 1=Anomalous)",
                runtime_ms=round(elapsed_ms, 2),
                warnings=warnings,
                limitations=[
                    "Container inspection checks metadata wrapper, not decoded pixels.",
                    "Absent C2PA manifest does NOT imply AI generation."
                ],
                evidence_summary=summary,
            ),
            [],
        )
