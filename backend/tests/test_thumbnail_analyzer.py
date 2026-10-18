import io
import os
import struct
import tempfile
import pytest
from PIL import Image

from app.schemas.evidence import ThumbnailStatus
from app.services.thumbnail_analyzer import analyze_embedded_thumbnail


def _build_synthetic_jpeg_with_thumbnail(
    main_size=(200, 200),
    thumb_size=(40, 40),
    mismatch=False,
    corrupt_magic=False,
    corrupt_data=False,
) -> bytes:
    main_img = Image.new("RGB", main_size, (180, 60, 60))
    for x in range(30, 80):
        for y in range(30, 80):
            main_img.putpixel((x, y), (60, 60, 200))

    if mismatch:
        thumb_img = Image.new("RGB", thumb_size, (20, 200, 20))
    else:
        thumb_img = main_img.resize(thumb_size, Image.Resampling.BILINEAR)

    thumb_buf = io.BytesIO()
    thumb_img.save(thumb_buf, format="JPEG", quality=85)
    thumb_bytes = thumb_buf.getvalue()

    if corrupt_magic:
        thumb_bytes = b"NOTAJPEG" + thumb_bytes[8:]
    elif corrupt_data:
        thumb_bytes = thumb_bytes[:8] + (bytes([0]) * 40)

    endian = "<"
    tiff_header = bytes([0x49, 0x49, 0x2a, 0, 8, 0, 0, 0])

    ifd0_entries = struct.pack(f"{endian}HHIHH", 0x0100, 3, 1, main_size[0], 0)
    ifd0_count = struct.pack(f"{endian}H", 1)
    ifd1_offset = 26
    next_ifd0 = struct.pack(f"{endian}I", ifd1_offset)

    thumb_offset = 56
    thumb_len = len(thumb_bytes)
    ifd1_count = struct.pack(f"{endian}H", 2)
    entry_thumb_off = struct.pack(f"{endian}HHII", 0x0201, 4, 1, thumb_offset)
    entry_thumb_len = struct.pack(f"{endian}HHII", 0x0202, 4, 1, thumb_len)
    next_ifd1 = struct.pack(f"{endian}I", 0)

    tiff_data = (
        tiff_header +
        ifd0_count + ifd0_entries + next_ifd0 +
        ifd1_count + entry_thumb_off + entry_thumb_len + next_ifd1 +
        thumb_bytes
    )
    exif_payload = bytes([0x45, 0x78, 0x69, 0x66, 0, 0]) + tiff_data
    main_buf = io.BytesIO()
    main_img.save(main_buf, format="JPEG", exif=exif_payload)
    return main_buf.getvalue()


def test_no_embedded_thumbnail():
    img = Image.new("RGB", (100, 100), (40, 80, 120))
    res = analyze_embedded_thumbnail(img)
    assert res.status == ThumbnailStatus.NO_THUMBNAIL
    assert res.has_thumbnail is False
    assert res.thumbnail_dimensions is None
    assert res.similarity_score is None


def test_valid_embedded_thumbnail_comparable():
    raw_jpeg = _build_synthetic_jpeg_with_thumbnail()
    img = Image.open(io.BytesIO(raw_jpeg))

    res = analyze_embedded_thumbnail(img)
    assert res.status == ThumbnailStatus.COMPARABLE
    assert res.has_thumbnail is True
    assert res.thumbnail_dimensions == {"width": 40, "height": 40}
    assert res.primary_dimensions == {"width": 200, "height": 200}
    assert res.similarity_score is not None
    assert res.similarity_score >= 0.85
    assert res.mean_absolute_difference is not None


def test_embedded_thumbnail_mismatch_observed():
    raw_jpeg = _build_synthetic_jpeg_with_thumbnail(mismatch=True)
    img = Image.open(io.BytesIO(raw_jpeg))

    res = analyze_embedded_thumbnail(img)
    assert res.status == ThumbnailStatus.MISMATCH_OBSERVED
    assert res.has_thumbnail is True
    assert res.similarity_score is not None
    assert res.similarity_score < 0.85
    assert "discrepancy" in res.comparison_notes.lower()


def test_unsupported_thumbnail_magic():
    raw_jpeg = _build_synthetic_jpeg_with_thumbnail(corrupt_magic=True)
    img = Image.open(io.BytesIO(raw_jpeg))

    res = analyze_embedded_thumbnail(img)
    assert res.status == ThumbnailStatus.UNAVAILABLE
    assert res.has_thumbnail is True
    assert "magic" in res.comparison_notes.lower()


def test_corrupted_thumbnail_data():
    raw_jpeg = _build_synthetic_jpeg_with_thumbnail(corrupt_data=True)
    img = Image.open(io.BytesIO(raw_jpeg))

    res = analyze_embedded_thumbnail(img)
    assert res.status == ThumbnailStatus.UNAVAILABLE
    assert res.has_thumbnail is True
    assert "corrupted" in res.comparison_notes.lower() or "undecodable" in res.comparison_notes.lower()


def test_thumbnail_deterministic_numerical_output():
    raw_jpeg = _build_synthetic_jpeg_with_thumbnail()
    img1 = Image.open(io.BytesIO(raw_jpeg))
    img2 = Image.open(io.BytesIO(raw_jpeg))

    res1 = analyze_embedded_thumbnail(img1)
    res2 = analyze_embedded_thumbnail(img2)

    assert res1.similarity_score == res2.similarity_score
    assert res1.mean_absolute_difference == res2.mean_absolute_difference
    assert res1.status == res2.status


def test_thumbnail_zero_disk_leakage():
    temp_dir = tempfile.gettempdir()
    before_files = set(os.listdir(temp_dir))

    raw_jpeg = _build_synthetic_jpeg_with_thumbnail()
    img = Image.open(io.BytesIO(raw_jpeg))
    res = analyze_embedded_thumbnail(img)

    after_files = set(os.listdir(temp_dir))
    new_files = after_files - before_files
    assert not any("thumb" in f.lower() or "secura" in f.lower() for f in new_files)
    assert res.has_thumbnail is True
