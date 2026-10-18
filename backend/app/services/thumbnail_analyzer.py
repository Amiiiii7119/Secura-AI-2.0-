import base64
import io
import struct
from typing import Dict, Optional, Tuple
import numpy as np
from PIL import Image, ImageOps

from app.schemas.evidence import ThumbnailAnalysisResult, ThumbnailStatus


def extract_raw_ifd1_thumbnail_bytes(exif_bytes: Optional[bytes]) -> Optional[bytes]:
    """
    Safely extract raw IFD1 embedded JPEG thumbnail bytes from raw EXIF binary payload.
    Supports both little-endian (II) and big-endian (MM) TIFF byte order.
    Returns raw JPEG bytes or None if absent or malformed.
    Strictly in-memory, bounded, and zero-disk.
    """
    if not exif_bytes or len(exif_bytes) < 14:
        return None

    # Handle standard 'Exif\x00\x00' TIFF header prefix
    header_offset = 0
    if exif_bytes.startswith(b"Exif\x00\x00"):
        header_offset = 6

    tiff_bytes = exif_bytes[header_offset:]
    if len(tiff_bytes) < 8:
        return None

    endian_marker = tiff_bytes[:2]
    if endian_marker == b"II":
        endian = "<"
    elif endian_marker == b"MM":
        endian = ">"
    else:
        return None

    try:
        magic = struct.unpack(f"{endian}H", tiff_bytes[2:4])[0]
        if magic != 42:
            return None

        ifd0_offset = struct.unpack(f"{endian}I", tiff_bytes[4:8])[0]
        if ifd0_offset + 2 > len(tiff_bytes):
            return None

        num_entries_0 = struct.unpack(f"{endian}H", tiff_bytes[ifd0_offset:ifd0_offset + 2])[0]
        ifd1_pointer_offset = ifd0_offset + 2 + num_entries_0 * 12
        if ifd1_pointer_offset + 4 > len(tiff_bytes):
            return None

        ifd1_offset = struct.unpack(f"{endian}I", tiff_bytes[ifd1_pointer_offset:ifd1_pointer_offset + 4])[0]
        if ifd1_offset == 0 or ifd1_offset + 2 > len(tiff_bytes):
            return None

        num_entries_1 = struct.unpack(f"{endian}H", tiff_bytes[ifd1_offset:ifd1_offset + 2])[0]
        thumb_offset = None
        thumb_length = None

        for i in range(num_entries_1):
            entry_pos = ifd1_offset + 2 + i * 12
            if entry_pos + 12 > len(tiff_bytes):
                break
            tag, typ, count, val = struct.unpack(f"{endian}HHI4s", tiff_bytes[entry_pos:entry_pos + 12])
            if tag == 0x0201:  # JPEGInterchangeFormat (thumbnail offset)
                thumb_offset = struct.unpack(f"{endian}I", val)[0]
            elif tag == 0x0202:  # JPEGInterchangeFormatLength (thumbnail byte count)
                thumb_length = struct.unpack(f"{endian}I", val)[0]

        if thumb_offset is not None and thumb_length is not None:
            if thumb_offset + thumb_length <= len(tiff_bytes) and thumb_length > 0:
                thumb_data = tiff_bytes[thumb_offset:thumb_offset + thumb_length]
                return thumb_data
    except Exception:
        return None

    return None


def analyze_embedded_thumbnail(
    primary_image: Image.Image,
    orientation_tag: Optional[int] = None,
) -> ThumbnailAnalysisResult:
    """
    Inspect and analyze embedded thumbnail in container metadata.
    Compares aligned thumbnail against primary image to detect visual discrepancies.
    """
    exif_bytes = primary_image.info.get("exif")
    fmt = (primary_image.format or "").upper()
    if not exif_bytes:
        notes = (
            f"No embedded thumbnail stream detected in {fmt or 'image'} container. "
            "Analysis confirmed absence of embedded IFD1 preview (standard for web media and stripped photographs)."
        )
        return ThumbnailAnalysisResult(
            status=ThumbnailStatus.THUMBNAIL_ABSENT,
            has_thumbnail=False,
            thumbnail_data_url=None,
            primary_dimensions={"width": primary_image.width, "height": primary_image.height},
            primary_aspect_ratio=round(primary_image.width / primary_image.height, 4) if primary_image.height > 0 else None,
            comparison_notes=notes,
        )

    thumb_bytes = extract_raw_ifd1_thumbnail_bytes(exif_bytes)
    if not thumb_bytes:
        return ThumbnailAnalysisResult(
            status=ThumbnailStatus.THUMBNAIL_ABSENT,
            has_thumbnail=False,
            thumbnail_data_url=None,
            primary_dimensions={"width": primary_image.width, "height": primary_image.height},
            primary_aspect_ratio=round(primary_image.width / primary_image.height, 4) if primary_image.height > 0 else None,
            comparison_notes="Analysis confirmed absence of embedded IFD1 thumbnail stream in EXIF structure.",
        )

    # Validate thumbnail magic bytes
    if not thumb_bytes.startswith(b"\xff\xd8\xff"):
        return ThumbnailAnalysisResult(
            status=ThumbnailStatus.THUMBNAIL_INVALID,
            has_thumbnail=True,
            thumbnail_data_url=None,
            thumbnail_format="UNKNOWN",
            primary_dimensions={"width": primary_image.width, "height": primary_image.height},
            primary_aspect_ratio=round(primary_image.width / primary_image.height, 4) if primary_image.height > 0 else None,
            comparison_notes="Thumbnail stream found in IFD1 but contains invalid JPEG header magic bytes.",
        )

    # Safely decode thumbnail in memory
    try:
        thumb_img = Image.open(io.BytesIO(thumb_bytes))
        thumb_img.load()
    except Exception as exc:
        return ThumbnailAnalysisResult(
            status=ThumbnailStatus.THUMBNAIL_INVALID,
            has_thumbnail=True,
            thumbnail_data_url=None,
            thumbnail_format="JPEG",
            primary_dimensions={"width": primary_image.width, "height": primary_image.height},
            primary_aspect_ratio=round(primary_image.width / primary_image.height, 4) if primary_image.height > 0 else None,
            comparison_notes=f"Thumbnail JPEG stream is corrupted or undecodable: {type(exc).__name__}",
        )

    t_w, t_h = thumb_img.size
    p_w, p_h = primary_image.size

    if t_w < 1 or t_h < 1:
        return ThumbnailAnalysisResult(
            status=ThumbnailStatus.UNAVAILABLE,
            has_thumbnail=True,
            thumbnail_format="JPEG",
            thumbnail_dimensions={"width": t_w, "height": t_h},
            primary_dimensions={"width": p_w, "height": p_h},
            comparison_notes="Thumbnail possesses degenerate zero dimensions.",
        )

    t_ar = round(t_w / t_h, 4)
    p_ar = round(p_w / p_h, 4) if p_h > 0 else None

    # Align primary image to thumbnail dimensions for comparison
    primary_rgb = primary_image.convert("RGB")
    thumb_rgb = thumb_img.convert("RGB")

    # Consider orientation transposition if orientation tag suggests transposed geometry
    candidates = [primary_rgb]
    if orientation_tag and orientation_tag in [5, 6, 7, 8]:
        # Tag 5-8 indicate 90 or 270 degree rotation
        candidates.append(primary_rgb.rotate(90, expand=True))
        candidates.append(primary_rgb.rotate(270, expand=True))

    best_mae = float("inf")
    thumb_np = np.asarray(thumb_rgb, dtype=np.float32)

    for cand in candidates:
        cand_resized = cand.resize((t_w, t_h), Image.Resampling.BILINEAR)
        cand_np = np.asarray(cand_resized, dtype=np.float32)
        mae = float(np.mean(np.abs(cand_np - thumb_np)))
        if mae < best_mae:
            best_mae = mae

    # Calculate normalized similarity in [0.0, 1.0]
    similarity_score = max(0.0, min(1.0, 1.0 - (best_mae / 255.0)))
    similarity_score = round(similarity_score, 4)
    best_mae = round(best_mae, 2)

    # Empirical heuristic threshold: >= 0.85 indicates visual concordance under standard downsampling.
    # Note: 0.85 is an empirical heuristic for lossy JPEG downsampling variance, not a scientifically validated tampering boundary.
    is_comparable = similarity_score >= 0.85
    status = ThumbnailStatus.COMPARABLE if is_comparable else ThumbnailStatus.MISMATCH_OBSERVED

    if is_comparable:
        notes = (
            f"Thumbnail extracted ({t_w}x{t_h}) vs primary image ({p_w}x{p_h}). "
            f"Visual similarity score: {similarity_score:.4f} (MAE: {best_mae:.2f}/255). "
            "Thumbnail content is visually consistent with primary image within expected downsampling and recompression tolerances (0.85 empirical heuristic threshold)."
        )
    else:
        notes = (
            f"Thumbnail extracted ({t_w}x{t_h}) vs primary image ({p_w}x{p_h}). "
            f"Visual similarity score: {similarity_score:.4f} (MAE: {best_mae:.2f}/255). "
            "Visual discrepancy observed between embedded thumbnail and primary image below the 0.85 empirical heuristic threshold. "
            "Forensic Context: Thumbnail differences commonly result from post-capture cropping, localized framing adjustments, "
            "differential color grading, or camera firmware preview generation. A mismatch does not establish synthetic AI generation or malicious tampering."
        )

    thumb_b64 = base64.b64encode(thumb_bytes).decode("ascii")
    thumb_url = f"data:image/jpeg;base64,{thumb_b64}"

    return ThumbnailAnalysisResult(
        status=status,
        has_thumbnail=True,
        thumbnail_data_url=thumb_url,
        thumbnail_format="JPEG",
        thumbnail_dimensions={"width": t_w, "height": t_h},
        primary_dimensions={"width": p_w, "height": p_h},
        thumbnail_aspect_ratio=t_ar,
        primary_aspect_ratio=p_ar,
        similarity_score=similarity_score,
        mean_absolute_difference=best_mae,
        comparison_notes=notes,
    )
