import io
import pytest
from PIL import Image
import numpy as np


@pytest.fixture
def valid_rgb_jpeg_bytes() -> bytes:
    """Generate in-memory valid RGB JPEG bytes."""
    img = Image.new("RGB", (100, 100), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@pytest.fixture
def valid_rgb_png_bytes() -> bytes:
    """Generate in-memory valid RGB PNG bytes."""
    img = Image.new("RGB", (100, 100), color=(32, 128, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def valid_rgba_png_bytes() -> bytes:
    """Generate in-memory valid RGBA PNG bytes with alpha transparency."""
    img = Image.new("RGBA", (80, 80), color=(200, 100, 50, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def valid_grayscale_jpeg_bytes() -> bytes:
    """Generate in-memory valid grayscale (L) JPEG bytes."""
    img = Image.new("L", (90, 90), color=180)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


@pytest.fixture
def uniform_image() -> Image.Image:
    """Generate a uniform color PIL image."""
    return Image.new("RGB", (64, 64), color=(100, 100, 100))


@pytest.fixture
def texture_image() -> Image.Image:
    """Generate a high-frequency noise texture PIL image."""
    arr = np.random.RandomState(42).randint(0, 256, (64, 64, 3), dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB")


@pytest.fixture
def spoofed_jpeg_bytes() -> bytes:
    """Bytes claiming to be a JPEG with extension but containing arbitrary text."""
    return b"Not a real JPEG content, just plain ASCII text"


@pytest.fixture
def corrupt_jpeg_bytes() -> bytes:
    """Bytes starting with JPEG magic bytes followed by truncated/corrupted garbage."""
    return b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00TRUNCATED_CORRUPT"


@pytest.fixture
def unsupported_format_bytes() -> bytes:
    """Generate a valid BMP image, which is unsupported by the endpoint."""
    img = Image.new("RGB", (50, 50), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    return buf.getvalue()
