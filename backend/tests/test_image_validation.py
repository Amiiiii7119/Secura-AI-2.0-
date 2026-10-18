import pytest
from PIL import Image
from app.core.config import settings
from app.schemas.evidence import ImageFormat
from app.services.image_validation import (
    ImageValidationError,
    detect_magic_format,
    validate_image_payload,
)


def test_detect_magic_format_jpeg(valid_rgb_jpeg_bytes):
    fmt = detect_magic_format(valid_rgb_jpeg_bytes)
    assert fmt == ImageFormat.JPEG


def test_detect_magic_format_png(valid_rgb_png_bytes):
    fmt = detect_magic_format(valid_rgb_png_bytes)
    assert fmt == ImageFormat.PNG


def test_detect_magic_format_unsupported(unsupported_format_bytes):
    with pytest.raises(ImageValidationError) as exc:
        detect_magic_format(unsupported_format_bytes)
    assert exc.value.status_code == 415
    assert exc.value.error_code == "UNSUPPORTED_MEDIA_TYPE"


def test_validate_image_payload_valid_jpeg(valid_rgb_jpeg_bytes):
    result, img = validate_image_payload(valid_rgb_jpeg_bytes, declared_filename="sample.jpg")
    assert result.is_valid is True
    assert result.detected_format == ImageFormat.JPEG
    assert result.width == 100
    assert result.height == 100
    assert result.pixel_count == 10000
    assert result.mime_type == "image/jpeg"
    assert img.size == (100, 100)


def test_validate_image_payload_valid_png(valid_rgb_png_bytes):
    result, img = validate_image_payload(valid_rgb_png_bytes, declared_filename="sample.png")
    assert result.is_valid is True
    assert result.detected_format == ImageFormat.PNG
    assert result.width == 100
    assert result.height == 100
    assert result.mime_type == "image/png"


def test_validate_image_payload_rgba(valid_rgba_png_bytes):
    result, img = validate_image_payload(valid_rgba_png_bytes, declared_filename="sample_alpha.png")
    assert result.is_valid is True
    assert result.color_mode == "RGBA"
    assert result.width == 80
    assert result.height == 80


def test_validate_image_payload_grayscale(valid_grayscale_jpeg_bytes):
    result, img = validate_image_payload(valid_grayscale_jpeg_bytes, declared_filename="sample_gray.jpg")
    assert result.is_valid is True
    assert result.color_mode == "L"
    assert result.width == 90
    assert result.height == 90


def test_validate_image_payload_empty_bytes():
    with pytest.raises(ImageValidationError) as exc:
        validate_image_payload(b"", declared_filename="empty.jpg")
    assert exc.value.status_code == 400
    assert exc.value.error_code == "EMPTY_FILE"


def test_validate_image_payload_oversized():
    fake_oversized = b"x" * (settings.MAX_UPLOAD_SIZE_BYTES + 1)
    with pytest.raises(ImageValidationError) as exc:
        validate_image_payload(fake_oversized, declared_filename="large.jpg")
    assert exc.value.status_code == 413
    assert exc.value.error_code == "PAYLOAD_TOO_LARGE"


def test_validate_image_payload_spoofed_file(spoofed_jpeg_bytes):
    with pytest.raises(ImageValidationError) as exc:
        validate_image_payload(spoofed_jpeg_bytes, declared_filename="fake.jpg")
    assert exc.value.status_code == 415


def test_validate_image_payload_corrupted_file(corrupt_jpeg_bytes):
    with pytest.raises(ImageValidationError) as exc:
        validate_image_payload(corrupt_jpeg_bytes, declared_filename="corrupt.jpg")
    assert exc.value.status_code == 400
    assert "CORRUPT" in exc.value.error_code or "DECODE" in exc.value.error_code


def test_validate_image_payload_decompression_bomb():
    # Construct an image that declares a huge size beyond settings.MAX_IMAGE_PIXELS
    # We temporarily set a low pixel cap to verify enforcement without allocating gigabytes of RAM
    original_cap = settings.MAX_IMAGE_PIXELS
    original_pil_cap = Image.MAX_IMAGE_PIXELS
    try:
        settings.MAX_IMAGE_PIXELS = 500  # Cap at 500 pixels for test
        # Generate an image of 100x100 = 10,000 pixels
        img = Image.new("RGB", (100, 100), color=(10, 20, 30))
        import io
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        
        with pytest.raises(ImageValidationError) as exc:
            validate_image_payload(buf.getvalue(), declared_filename="bomb.jpg")
        assert exc.value.status_code == 400
        assert "DECOMPRESSION_BOMB_LIMIT" in exc.value.error_code or "PIXEL_COUNT_EXCEEDED" in exc.value.error_code
    finally:
        settings.MAX_IMAGE_PIXELS = original_cap
        Image.MAX_IMAGE_PIXELS = original_pil_cap
