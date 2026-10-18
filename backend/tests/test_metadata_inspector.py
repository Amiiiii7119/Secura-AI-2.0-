import io
import pytest
from PIL import Image, ExifTags, PngImagePlugin

from app.schemas.evidence import ImageFormat, ImageValidationResult, MetadataStatus
from app.services.metadata_inspector import inspect_metadata


def _dummy_validation(width=100, height=100, fmt=ImageFormat.JPEG, size=1000) -> ImageValidationResult:
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


def test_jpeg_with_full_exif_metadata():
    img = Image.new("RGB", (200, 150), (120, 80, 40))
    exif = img.getexif()
    exif[ExifTags.Base.Make] = "Sony"
    exif[ExifTags.Base.Model] = "ILCE-7RM5"
    exif[ExifTags.Base.Software] = "Lightroom Classic 13.0"
    exif[ExifTags.Base.Orientation] = 1
    exif[ExifTags.Base.DateTime] = "2026:02:15 14:30:00"

    sub = exif.get_ifd(ExifTags.IFD.Exif)
    sub[ExifTags.Base.DateTimeOriginal] = "2026:02:15 10:15:00"
    sub[ExifTags.Base.DateTimeDigitized] = "2026:02:15 10:15:00"
    sub[ExifTags.Base.LensModel] = "FE 24-70mm F2.8 GM II"
    sub[ExifTags.Base.ExifImageWidth] = 200
    sub[ExifTags.Base.ExifImageHeight] = 150
    sub[ExifTags.Base.OffsetTimeOriginal] = "+01:00"

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw_bytes = buf.getvalue()

    loaded = Image.open(io.BytesIO(raw_bytes))
    val = _dummy_validation(width=200, height=150, fmt=ImageFormat.JPEG, size=len(raw_bytes))

    result = inspect_metadata(loaded, raw_bytes, val)

    assert result.inventory.status == MetadataStatus.PRESENT
    assert "EXIF" in result.inventory.detected_structures
    assert result.camera_metadata is not None
    assert result.camera_metadata.make == "Sony"
    assert result.camera_metadata.model == "ILCE-7RM5"
    assert result.camera_metadata.lens_model == "FE 24-70mm F2.8 GM II"
    assert result.camera_metadata.software == "Lightroom Classic 13.0"
    assert result.camera_metadata.orientation_tag == 1
    assert "Top-left" in (result.camera_metadata.orientation_description or "")
    assert result.camera_metadata.date_time_original == "2026:02:15 10:15:00"
    assert result.camera_metadata.date_time_modified == "2026:02:15 14:30:00"
    assert result.camera_metadata.offset_time == "+01:00"
    assert result.camera_metadata.metadata_dimensions == {"width": 200, "height": 150}


def test_jpeg_without_exif_metadata():
    img = Image.new("RGB", (100, 100), (50, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw_bytes = buf.getvalue()

    loaded = Image.open(io.BytesIO(raw_bytes))
    val = _dummy_validation(width=100, height=100, fmt=ImageFormat.JPEG, size=len(raw_bytes))

    result = inspect_metadata(loaded, raw_bytes, val)
    assert result.inventory.status == MetadataStatus.ABSENT
    assert len(result.inventory.detected_structures) == 0
    assert result.gps_summary.gps_present is False
    assert result.thumbnail_analysis.has_thumbnail is False


def test_png_with_text_metadata_chunks():
    img = Image.new("RGB", (80, 80), (30, 60, 90))
    info = PngImagePlugin.PngInfo()
    info.add_text("Software", "Adobe Photoshop 2024")
    info.add_text("Comment", "Generated for unit testing")

    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=info)
    raw_bytes = buf.getvalue()

    loaded = Image.open(io.BytesIO(raw_bytes))
    val = _dummy_validation(width=80, height=80, fmt=ImageFormat.PNG, size=len(raw_bytes))

    result = inspect_metadata(loaded, raw_bytes, val)
    assert result.inventory.status == MetadataStatus.PRESENT
    assert "PNG_TEXT" in result.inventory.detected_structures
    assert result.inventory.png_text_chunks_count >= 2
    assert result.camera_metadata is not None
    assert result.camera_metadata.software == "Adobe Photoshop 2024"


def test_png_without_metadata():
    img = Image.new("RGB", (64, 64), (10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    loaded = Image.open(io.BytesIO(raw_bytes))
    val = _dummy_validation(width=64, height=64, fmt=ImageFormat.PNG, size=len(raw_bytes))

    result = inspect_metadata(loaded, raw_bytes, val)
    assert result.inventory.status == MetadataStatus.ABSENT
    assert result.camera_metadata is not None
    assert result.camera_metadata.device_status.value == 'ABSENT'
    assert 'not present' in result.camera_metadata.device_display_text


def test_orientation_tags_and_descriptions():
    for tag_val in [1, 3, 6, 8]:
        img = Image.new("RGB", (100, 100))
        exif = img.getexif()
        exif[ExifTags.Base.Orientation] = tag_val
        buf = io.BytesIO()
        img.save(buf, format="JPEG", exif=exif)
        raw_bytes = buf.getvalue()

        loaded = Image.open(io.BytesIO(raw_bytes))
        val = _dummy_validation(width=100, height=100, fmt=ImageFormat.JPEG, size=len(raw_bytes))
        res = inspect_metadata(loaded, raw_bytes, val)
        assert res.camera_metadata is not None
        assert res.camera_metadata.orientation_tag == tag_val
        assert res.camera_metadata.orientation_description is not None


def test_gps_presence_without_coordinate_leakage():
    img = Image.new("RGB", (100, 100))
    exif = img.getexif()
    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps_ifd[1] = "N"
    gps_ifd[2] = 48.8584  # Eiffel tower latitude
    gps_ifd[3] = "E"
    gps_ifd[4] = 2.2945

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw_bytes = buf.getvalue()

    loaded = Image.open(io.BytesIO(raw_bytes))
    val = _dummy_validation(width=100, height=100, fmt=ImageFormat.JPEG, size=len(raw_bytes))

    # Test default privacy-safe extraction (opt-in disabled)
    result = inspect_metadata(loaded, raw_bytes, val, allow_gps_extraction=False)

    assert result.gps_summary.gps_present is True
    assert result.gps_summary.gps_status == "DETECTED_AND_REDACTED"
    assert result.gps_summary.tag_count >= 2
    assert result.gps_summary.coordinates_redacted is True
    assert result.gps_summary.latitude is None
    assert result.gps_summary.longitude is None
    assert "redacted" in result.gps_summary.privacy_notice.lower()


def test_malformed_metadata_header_handling():
    img = Image.new("RGB", (50, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    valid_bytes = buf.getvalue()

    # Inject corrupt EXIF marker
    corrupt_bytes = valid_bytes[:2] + b"\xFF\xE1\x00\x10Exif\x00\x00CORRUPT_HEADER_GARBAGE" + valid_bytes[2:]

    try:
        loaded = Image.open(io.BytesIO(corrupt_bytes))
    except Exception:
        pytest.skip("Pillow rejected corrupt header at container level")

    val = _dummy_validation(width=50, height=50, fmt=ImageFormat.JPEG, size=len(corrupt_bytes))
    result = inspect_metadata(loaded, corrupt_bytes, val)

    # Must return a valid schema object without raising uncaught exceptions
    assert result.inventory.status in [MetadataStatus.MALFORMED, MetadataStatus.ABSENT, MetadataStatus.PARTIAL]
    assert isinstance(result.analysis_notes, str)


def test_xmp_packet_detection_in_raw_bytes():
    img = Image.new("RGB", (50, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw_bytes = buf.getvalue()

    # Append simulated Adobe XMP packet
    xmp_raw = raw_bytes + b"<x:xmpmeta xmlns:x='adobe:ns:meta/'><rdf:RDF xmlns:rdf='http://ns.adobe.com/xap/1.0/'></rdf:RDF></x:xmpmeta>"
    loaded = Image.open(io.BytesIO(raw_bytes))
    val = _dummy_validation(width=50, height=50, fmt=ImageFormat.JPEG, size=len(xmp_raw))

    result = inspect_metadata(loaded, xmp_raw, val)
    assert result.inventory.xmp_packet_present is True
    assert "XMP" in result.inventory.detected_structures


def test_metadata_result_json_serialization():
    img = Image.new("RGB", (60, 60))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw = buf.getvalue()
    loaded = Image.open(io.BytesIO(raw))
    val = _dummy_validation(width=60, height=60, fmt=ImageFormat.JPEG, size=len(raw))

    res = inspect_metadata(loaded, raw, val)
    dumped = res.model_dump()
    json_str = res.model_dump_json()

    assert isinstance(dumped, dict)
    assert "inventory" in dumped
    assert "gps_summary" in dumped
    assert isinstance(json_str, str)
