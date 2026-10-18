import io
from typing import Tuple
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.schemas.evidence import ImageFormat, ImageValidationResult


# Exact magic byte signatures
JPEG_MAGIC = b"\xFF\xD8\xFF"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class ImageValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "IMAGE_VALIDATION_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def detect_magic_format(data: bytes) -> ImageFormat:
    """Detect image format by inspecting explicit magic byte signatures.
    
    Limitation: Magic byte validation verifies headers only; it does not replace
    comprehensive decoding, sanitization, or malware analysis.
    """
    if len(data) < 8:
        raise ImageValidationError("File is too small to contain a valid image header", status_code=400, error_code="FILE_TOO_SMALL")
    
    if data.startswith(JPEG_MAGIC):
        return ImageFormat.JPEG
    elif data.startswith(PNG_MAGIC):
        return ImageFormat.PNG
    else:
        raise ImageValidationError(
            "Unsupported file signature. Only authentic JPEG and PNG formats are accepted.",
            status_code=415,
            error_code="UNSUPPORTED_MEDIA_TYPE"
        )


def validate_image_payload(data: bytes, declared_filename: str = "") -> Tuple[ImageValidationResult, Image.Image]:
    """Validate uploaded image data against size, magic bytes, Pillow decodability, and pixel caps.
    
    Returns:
        Tuple of (ImageValidationResult schema, decoded PIL Image object)
    """
    file_size = len(data)
    if file_size == 0:
        raise ImageValidationError("Uploaded file is empty (0 bytes)", status_code=400, error_code="EMPTY_FILE")
    
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mib = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise ImageValidationError(
            f"File size ({file_size} bytes) exceeds the maximum allowed limit of {max_mib} MiB.",
            status_code=413,
            error_code="PAYLOAD_TOO_LARGE"
        )
    
    # 1. Inspect magic bytes
    detected_format = detect_magic_format(data)
    
    # 2. Decode with Pillow and enforce pixel limits
    try:
        # We configure Pillow decompression bomb protection
        Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS
        
        stream = io.BytesIO(data)
        img = Image.open(stream)
        
        # Verify image integrity and ensure file structure is valid
        # Note: img.verify() only checks headers; calling img.load() forces decoding of all pixel data
        img.load()
        
    except Image.DecompressionBombError as e:
        raise ImageValidationError(
            f"Image dimensions exceed safe pixel limits (decompression bomb protection): {str(e)}",
            status_code=400,
            error_code="DECOMPRESSION_BOMB_LIMIT"
        )
    except (UnidentifiedImageError, OSError, SyntaxError) as e:
        raise ImageValidationError(
            f"Image is corrupted, malformed, or cannot be decoded: {str(e)}",
            status_code=400,
            error_code="CORRUPT_OR_MALFORMED_IMAGE"
        )
    except Exception as e:
        raise ImageValidationError(
            f"Unexpected error decoding image: {str(e)}",
            status_code=400,
            error_code="DECODE_ERROR"
        )
    
    width, height = img.size
    if width < 1 or height < 1:
        raise ImageValidationError("Image dimensions must be at least 1x1 pixels", status_code=400, error_code="INVALID_DIMENSIONS")
    
    pixel_count = width * height
    if pixel_count > settings.MAX_IMAGE_PIXELS:
        raise ImageValidationError(
            f"Pixel count ({pixel_count}) exceeds safe ceiling ({settings.MAX_IMAGE_PIXELS})",
            status_code=400,
            error_code="PIXEL_COUNT_EXCEEDED"
        )
    
    # Verify Pillow format agrees with detected magic format
    pil_format = img.format.upper() if img.format else ""
    if detected_format == ImageFormat.JPEG and pil_format not in ("JPEG", "MPO"):
        raise ImageValidationError(
            f"Format mismatch: header indicates JPEG but decoder identified {pil_format}",
            status_code=400,
            error_code="FORMAT_MISMATCH"
        )
    elif detected_format == ImageFormat.PNG and pil_format != "PNG":
        raise ImageValidationError(
            f"Format mismatch: header indicates PNG but decoder identified {pil_format}",
            status_code=400,
            error_code="FORMAT_MISMATCH"
        )
    
    mime_type = "image/jpeg" if detected_format == ImageFormat.JPEG else "image/png"
    
    result = ImageValidationResult(
        is_valid=True,
        detected_format=detected_format,
        width=width,
        height=height,
        pixel_count=pixel_count,
        color_mode=img.mode,
        file_size_bytes=file_size,
        mime_type=mime_type
    )
    
    return result, img
