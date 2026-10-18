import io
from PIL import Image, ExifTags

from app.schemas.evidence import (
    ConsistencySeverity,
    ImageFormat,
    ImageValidationResult,
)
from app.services.metadata_inspector import inspect_metadata


def _dummy_validation(width=200, height=150, fmt=ImageFormat.JPEG, size=2000) -> ImageValidationResult:
    return ImageValidationResult(
        is_valid=True,
        detected_format=fmt,
        width=width,
        height=height,
        pixel_count=width * height,
        color_mode="RGB",
        file_size_bytes=size,
        mime_type="image/jpeg" if fmt == ImageFormat.JPEG else "image/png"
    )


def test_dimension_mismatch_inconsistency():
    img = Image.new("RGB", (200, 150))
    exif = img.getexif()
    sub = exif.get_ifd(ExifTags.IFD.Exif)
    sub[ExifTags.Base.ExifImageWidth] = 400  # Mismatched recorded width!
    sub[ExifTags.Base.ExifImageHeight] = 300

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw = buf.getvalue()

    loaded = Image.open(io.BytesIO(raw))
    val = _dummy_validation(width=200, height=150, fmt=ImageFormat.JPEG, size=len(raw))
    res = inspect_metadata(loaded, raw, val)

    assert res.container_consistency.status == "DISCREPANCIES_OBSERVED"
    dim_obs = next((o for o in res.container_consistency.observations if o.check_name == "dimension_concordance"), None)
    assert dim_obs is not None
    assert dim_obs.severity == ConsistencySeverity.INCONSISTENCY
    assert "200x150" in dim_obs.observed_state
    assert "400x300" in dim_obs.observed_state
    assert "cropped" in dim_obs.benign_explanation.lower()


def test_timestamp_chronology_inconsistency():
    img = Image.new("RGB", (100, 100))
    exif = img.getexif()
    exif[ExifTags.Base.DateTime] = "2026:01:01 00:00:00"  # Modified first
    sub = exif.get_ifd(ExifTags.IFD.Exif)
    sub[ExifTags.Base.DateTimeOriginal] = "2026:01:05 12:00:00"  # Original capture supposedly later!

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw = buf.getvalue()

    loaded = Image.open(io.BytesIO(raw))
    val = _dummy_validation(width=100, height=100, fmt=ImageFormat.JPEG, size=len(raw))
    res = inspect_metadata(loaded, raw, val)

    assert res.container_consistency.status == "DISCREPANCIES_OBSERVED"
    ts_obs = next((o for o in res.container_consistency.observations if o.check_name == "timestamp_chronology"), None)
    assert ts_obs is not None
    assert ts_obs.severity == ConsistencySeverity.INCONSISTENCY
    assert "chronologically after" in ts_obs.observed_state


def test_software_editing_indicator():
    img = Image.new("RGB", (100, 100))
    exif = img.getexif()
    exif[ExifTags.Base.Software] = "Adobe Photoshop 25.0 (Windows)"

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw = buf.getvalue()

    loaded = Image.open(io.BytesIO(raw))
    val = _dummy_validation(width=100, height=100, fmt=ImageFormat.JPEG, size=len(raw))
    res = inspect_metadata(loaded, raw, val)

    sw_obs = next((o for o in res.container_consistency.observations if o.check_name == "software_editing_indicator"), None)
    assert sw_obs is not None
    assert sw_obs.severity == ConsistencySeverity.INFO
    assert "Photoshop" in sw_obs.observed_state
    assert "routine photo editing" in sw_obs.benign_explanation.lower()


def test_orientation_geometry_concordance():
    # Tag 6 is rotated 90 CW (portrait), but raster is landscape (200x100)
    img = Image.new("RGB", (200, 100))
    exif = img.getexif()
    exif[ExifTags.Base.Orientation] = 6

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw = buf.getvalue()

    loaded = Image.open(io.BytesIO(raw))
    val = _dummy_validation(width=200, height=100, fmt=ImageFormat.JPEG, size=len(raw))
    res = inspect_metadata(loaded, raw, val)

    orient_obs = next((o for o in res.container_consistency.observations if o.check_name == "orientation_geometry_concordance"), None)
    assert orient_obs is not None
    assert orient_obs.severity == ConsistencySeverity.INFO
