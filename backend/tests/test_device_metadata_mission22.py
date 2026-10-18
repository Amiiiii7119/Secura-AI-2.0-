import io
import pytest
from PIL import Image, ExifTags, PngImagePlugin
from app.schemas.evidence import (
    DeviceMetadataStatus,
    ImageValidationResult,
    ImageFormat,
)
from app.services.metadata_inspector import inspect_metadata


def _make_dummy_val_result(w: int = 100, h: int = 100, fmt: ImageFormat = ImageFormat.JPEG) -> ImageValidationResult:
    return ImageValidationResult(
        is_valid=True,
        width=w,
        height=h,
        pixel_count=w * h,
        color_mode="RGB",
        aspect_ratio=w / h,
        detected_format=fmt,
        file_size_bytes=1000,
        sha256_hash="dummyhash",
        mime_type="image/jpeg" if fmt == ImageFormat.JPEG else "image/png",
    )


def test_scenario_1_jpeg_with_make_and_model():
    """Scenario 1: Camera manufacturer and model are present."""
    img = Image.new("RGB", (100, 100), color=(120, 150, 180))
    exif = img.getexif()
    exif[ExifTags.Base.Make] = "Sony"
    exif[ExifTags.Base.Model] = "ILCE-7RM4"
    exif[ExifTags.Base.Software] = "v1.20"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw_bytes = buf.getvalue()

    opened = Image.open(io.BytesIO(raw_bytes))
    val_res = _make_dummy_val_result()
    res = inspect_metadata(image=opened, raw_bytes=raw_bytes, validation_result=val_res)

    assert res.camera_metadata is not None
    assert res.camera_metadata.make == "Sony"
    assert res.camera_metadata.model == "ILCE-7RM4"
    assert res.camera_metadata.device_status == DeviceMetadataStatus.PRESENT
    assert res.camera_metadata.device_display_text == "Sony ILCE-7RM4"


def test_scenario_2_jpeg_with_make_only():
    """Scenario 2: Only manufacturer is present; model is unavailable."""
    img = Image.new("RGB", (100, 100), color=(120, 150, 180))
    exif = img.getexif()
    exif[ExifTags.Base.Make] = "Canon"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw_bytes = buf.getvalue()

    opened = Image.open(io.BytesIO(raw_bytes))
    val_res = _make_dummy_val_result()
    res = inspect_metadata(image=opened, raw_bytes=raw_bytes, validation_result=val_res)

    assert res.camera_metadata is not None
    assert res.camera_metadata.make == "Canon"
    assert res.camera_metadata.model is None
    assert res.camera_metadata.device_status == DeviceMetadataStatus.MANUFACTURER_ONLY
    assert res.camera_metadata.device_display_text == "Canon (Model unavailable)"


def test_scenario_3_image_without_exif():
    """Scenario 3: Metadata removed or file contains no device information."""
    img = Image.new("RGB", (100, 100), color=(50, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw_bytes = buf.getvalue()

    opened = Image.open(io.BytesIO(raw_bytes))
    val_res = _make_dummy_val_result()
    res = inspect_metadata(image=opened, raw_bytes=raw_bytes, validation_result=val_res)

    assert res.camera_metadata is not None
    assert res.camera_metadata.device_status == DeviceMetadataStatus.ABSENT
    assert res.camera_metadata.device_display_text == "Device information not present in file"


def test_scenario_4_malformed_exif():
    """Scenario 4: Metadata is malformed or corrupted."""
    img = Image.new("RGB", (100, 100), color=(80, 80, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw_valid = buf.getvalue()
    corrupted_bytes = raw_valid[:2] + b"\xff\xe1\x00\x10CorruptedExif\x00\x00" + raw_valid[2:]

    opened = Image.open(io.BytesIO(corrupted_bytes))
    val_res = _make_dummy_val_result()
    res = inspect_metadata(image=opened, raw_bytes=corrupted_bytes, validation_result=val_res)

    assert res.camera_metadata is not None
    assert res.camera_metadata.device_status in (DeviceMetadataStatus.MALFORMED, DeviceMetadataStatus.ABSENT)
    if res.camera_metadata.device_status == DeviceMetadataStatus.MALFORMED:
        assert res.camera_metadata.device_display_text == "Device metadata could not be read"


def test_scenario_5_png_with_and_without_metadata():
    """Scenario 5: PNG with and without supported metadata."""
    img_plain = Image.new("RGB", (100, 100), color=(90, 90, 90))
    buf_plain = io.BytesIO()
    img_plain.save(buf_plain, format="PNG")
    raw_plain = buf_plain.getvalue()
    opened_plain = Image.open(io.BytesIO(raw_plain))
    res_plain = inspect_metadata(image=opened_plain, raw_bytes=raw_plain, validation_result=_make_dummy_val_result(fmt=ImageFormat.PNG))

    assert res_plain.camera_metadata is not None
    assert res_plain.camera_metadata.device_status == DeviceMetadataStatus.ABSENT
    assert res_plain.camera_metadata.device_display_text == "Device information not present in file"

    png_info = PngImagePlugin.PngInfo()
    png_info.add_text("Software", "Adobe Photoshop 2024")
    buf_meta = io.BytesIO()
    img_plain.save(buf_meta, format="PNG", pnginfo=png_info)
    raw_meta = buf_meta.getvalue()
    opened_meta = Image.open(io.BytesIO(raw_meta))
    res_meta = inspect_metadata(image=opened_meta, raw_bytes=raw_meta, validation_result=_make_dummy_val_result(fmt=ImageFormat.PNG))

    assert res_meta.camera_metadata is not None
    assert res_meta.camera_metadata.device_status == DeviceMetadataStatus.SOFTWARE_ONLY
    assert "Adobe Photoshop 2024" in res_meta.camera_metadata.device_display_text


def test_scenario_6_software_only_no_camera():
    """Scenario 6: File with software metadata but no camera metadata."""
    img = Image.new("RGB", (100, 100), color=(20, 40, 60))
    exif = img.getexif()
    exif[ExifTags.Base.Software] = "Midjourney v6.0"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw_bytes = buf.getvalue()

    opened = Image.open(io.BytesIO(raw_bytes))
    val_res = _make_dummy_val_result()
    res = inspect_metadata(image=opened, raw_bytes=raw_bytes, validation_result=val_res)

    assert res.camera_metadata is not None
    assert res.camera_metadata.device_status == DeviceMetadataStatus.SOFTWARE_ONLY
    assert res.camera_metadata.device_display_text == "Software: Midjourney v6.0"
    assert res.camera_metadata.make is None
    assert res.camera_metadata.model is None
