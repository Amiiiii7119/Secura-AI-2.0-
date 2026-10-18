"""Deterministic in-memory synthetic fixture generator for Secura AI 2.0 evaluation.

Generates 16 controlled test fixtures to systematically evaluate:
- In-memory Error Level Analysis (ELA)
- Discrete Cosine Transform (DCT) & 8x8 block-boundary discontinuities
- High-pass Laplacian noise residual proxies
- Format validation and edge-case handling

All fixtures are generated purely in memory with fixed random seeds for complete reproducibility.
No external network calls, pretrained weights, or persistent disk files are utilized.
"""

import io
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image


class SyntheticFixture:
    def __init__(
        self,
        fixture_id: str,
        name: str,
        description: str,
        construction_method: str,
        intended_test_property: str,
        format_name: str,
        pil_image: Optional[Image.Image] = None,
        raw_bytes: Optional[bytes] = None,
        dimensions: Optional[Tuple[int, int]] = None
    ):
        self.fixture_id = fixture_id
        self.name = name
        self.description = description
        self.construction_method = construction_method
        self.intended_test_property = intended_test_property
        self.format_name = format_name
        self.pil_image = pil_image
        self.raw_bytes = raw_bytes
        self.dimensions = dimensions or (pil_image.size if pil_image else (0, 0))


def generate_all_fixtures() -> List[SyntheticFixture]:
    """Generate the full battery of 16 controlled synthetic fixtures in memory."""
    fixtures: List[SyntheticFixture] = []
    
    # 1. Uniform RGB Image
    img_uniform = Image.new("RGB", (64, 64), color=(128, 128, 128))
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-01-UNIFORM-RGB",
            name="Uniform RGB Flat Field",
            description="Completely uniform neutral gray flat field canvas.",
            construction_method="Image.new('RGB', (64, 64), color=(128, 128, 128))",
            intended_test_property="Zero spatial variance, zero Laplacian residual, minimal ELA diff.",
            format_name="RAW_PIL",
            pil_image=img_uniform
        )
    )

    # 2. Smooth Linear Gradient
    grad_arr = np.tile(np.linspace(0, 255, 64, dtype=np.uint8), (64, 1))
    grad_rgb = np.stack([grad_arr, grad_arr, grad_arr], axis=-1)
    img_grad = Image.fromarray(grad_rgb, mode="RGB")
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-02-SMOOTH-GRADIENT",
            name="Smooth Horizontal Gradient",
            description="Continuous linear luminance ramp across horizontal axis.",
            construction_method="np.linspace(0, 255, 64) tiled vertically across 64 rows",
            intended_test_property="Smooth continuous spatial transition without abrupt grid boundaries.",
            format_name="RAW_PIL",
            pil_image=img_grad
        )
    )

    # 3. Textured Procedural Wave Pattern
    x = np.linspace(0, 4 * np.pi, 64)
    y = np.linspace(0, 4 * np.pi, 64)
    xx, yy = np.meshgrid(x, y)
    pattern = ((np.sin(xx) * np.cos(yy) + 1.0) * 127.5).astype(np.uint8)
    img_texture = Image.fromarray(np.stack([pattern, pattern, pattern], axis=-1), mode="RGB")
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-03-TEXTURED-PROCEDURAL",
            name="Procedural Sinusoidal Texture",
            description="Continuous 2D wave surface generating predictable periodic texture.",
            construction_method="sin(x) * cos(y) evaluated on 64x64 grid mapped to [0, 255]",
            intended_test_property="Non-zero AC frequency energy and continuous non-zero residual.",
            format_name="RAW_PIL",
            pil_image=img_texture
        )
    )

    # 4. Deterministic High-Frequency Noise
    rng = np.random.RandomState(42)
    noise_arr = rng.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    img_noise = Image.fromarray(noise_arr, mode="RGB")
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-04-HF-NOISE",
            name="Deterministic High-Frequency Noise",
            description="Seeded pseudo-random uniform noise with maximum spatial entropy.",
            construction_method="np.random.RandomState(42).randint(0, 256, (64, 64, 3))",
            intended_test_property="Elevated Laplacian noise residual magnitude and high AC block energy.",
            format_name="RAW_PIL",
            pil_image=img_noise
        )
    )

    # 5. Deliberate 8x8-Aligned Block Discontinuities
    aligned_grid = np.zeros((64, 64), dtype=np.uint8)
    for r in range(8):
        for c in range(8):
            if (r + c) % 2 == 0:
                aligned_grid[r*8:(r+1)*8, c*8:(c+1)*8] = 220
            else:
                aligned_grid[r*8:(r+1)*8, c*8:(c+1)*8] = 35
    img_aligned = Image.fromarray(np.stack([aligned_grid]*3, axis=-1), mode="RGB")
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-05-ALIGNED-8X8-BLOCKS",
            name="8x8 Grid-Aligned Checkerboard",
            description="Step discontinuities situated strictly at lines x=8k and y=8k.",
            construction_method="64x64 canvas tiled with alternating 8x8 constant blocks (220 vs 35)",
            intended_test_property="Pronounced step discontinuity across boundary with 0 internal step (high BAR).",
            format_name="RAW_PIL",
            pil_image=img_aligned
        )
    )

    # 6. Deliberate Non-Aligned Discontinuities (Shifted Grid)
    non_aligned_grid = np.roll(np.roll(aligned_grid, 3, axis=0), 3, axis=1)
    img_non_aligned = Image.fromarray(np.stack([non_aligned_grid]*3, axis=-1), mode="RGB")
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-06-NON-ALIGNED-DISCONTINUITY",
            name="Shifted Block Discontinuities",
            description="Step discontinuities shifted by 3 pixels away from 8x8 boundary grid.",
            construction_method="np.roll(aligned_grid, (3, 3)) displacing discontinuities to x=8k+3",
            intended_test_property="Internal discontinuity exceeds boundary discontinuity (low BAR < 1.0).",
            format_name="RAW_PIL",
            pil_image=img_non_aligned
        )
    )

    # 7. RGB Divisible by Eight
    img_div8 = Image.new("RGB", (64, 64), color=(90, 110, 130))
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-07-DIVISIBLE-BY-8",
            name="Dimensions Exact Multiple of 8",
            description="64x64 image where width and height are exact multiples of 8.",
            construction_method="Image.new('RGB', (64, 64))",
            intended_test_property="Analyzed grid dimensions equal full canvas dimensions with 0 remainder.",
            format_name="RAW_PIL",
            pil_image=img_div8
        )
    )

    # 8. RGB Non-Divisible by Eight
    img_nondiv8 = Image.new("RGB", (67, 73), color=(90, 110, 130))
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-08-NON-DIVISIBLE-BY-8",
            name="Dimensions Non-Divisible by 8",
            description="67x73 image with 3 remainder pixels in X and 1 remainder pixel in Y.",
            construction_method="Image.new('RGB', (67, 73))",
            intended_test_property="Analyzed grid truncates safely to 64x72 (8x9 blocks) with documented remainder.",
            format_name="RAW_PIL",
            pil_image=img_nondiv8
        )
    )

    # 9. Grayscale Image (Mode L)
    img_gray = Image.new("L", (64, 64), color=150)
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-09-GRAYSCALE",
            name="Single-Channel Grayscale (Mode L)",
            description="64x64 single-channel 8-bit luminance image.",
            construction_method="Image.new('L', (64, 64), color=150)",
            intended_test_property="Handles 2D single channel cleanly across ELA, DCT, and Noise without dimension error.",
            format_name="RAW_PIL",
            pil_image=img_gray
        )
    )

    # 10. RGBA with Alpha Transparency
    rgba_arr = np.zeros((64, 64, 4), dtype=np.uint8)
    rgba_arr[:, :32, :] = [255, 0, 0, 0]    # Left half: Transparent red
    rgba_arr[:, 32:, :] = [0, 255, 0, 255]  # Right half: Opaque green
    img_rgba = Image.fromarray(rgba_arr, mode="RGBA")
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-10-RGBA-TRANSPARENCY",
            name="RGBA with Transparency",
            description="64x64 RGBA canvas with 50% fully transparent pixels and 50% opaque pixels.",
            construction_method="Constructed array with alpha=0 on left half and alpha=255 on right half",
            intended_test_property="Composites alpha=0 onto opaque background rather than processing hidden RGB values.",
            format_name="RAW_PIL",
            pil_image=img_rgba
        )
    )

    # 11. Valid Encoded JPEG Payload
    buf_jpeg = io.BytesIO()
    img_grad.save(buf_jpeg, format="JPEG", quality=90)
    jpeg_bytes = buf_jpeg.getvalue()
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-11-VALID-JPEG",
            name="Encoded Valid JPEG",
            description="Standard valid JPEG compressed at quality factor 90.",
            construction_method="In-memory save to JPEG with PIL quality=90",
            intended_test_property="Validates magic bytes (FF D8 FF), decodes, and measures standard baseline.",
            format_name="JPEG",
            pil_image=img_grad,
            raw_bytes=jpeg_bytes
        )
    )

    # 12. Valid Encoded Lossless PNG Payload
    buf_png = io.BytesIO()
    img_grad.save(buf_png, format="PNG")
    png_bytes = buf_png.getvalue()
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-12-LOSSLESS-PNG",
            name="Encoded Lossless PNG",
            description="Lossless PNG encoding of identical gradient image.",
            construction_method="In-memory save to PNG format",
            intended_test_property="Validates PNG magic bytes, documents absence of initial JPEG compression.",
            format_name="PNG",
            pil_image=img_grad,
            raw_bytes=png_bytes
        )
    )

    # 13. Recompressed JPEG (Q50 followed by Q90)
    buf_q50 = io.BytesIO()
    img_texture.save(buf_q50, format="JPEG", quality=50)
    buf_q50.seek(0)
    img_from_q50 = Image.open(buf_q50)
    buf_recomp = io.BytesIO()
    img_from_q50.save(buf_recomp, format="JPEG", quality=90)
    recomp_bytes = buf_recomp.getvalue()
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-13-RECOMPRESSED-JPEG",
            name="Recompressed Dual-Quality JPEG",
            description="Image compressed first at low quality (Q50), then re-encoded at Q90.",
            construction_method="Encode Q50 -> decode -> encode Q90 in memory",
            intended_test_property="Exhibits dual-quantization error characteristics under ELA.",
            format_name="JPEG",
            pil_image=img_from_q50,
            raw_bytes=recomp_bytes
        )
    )

    # 14. PNG Converted from Known Lossy JPEG
    buf_png_from_jpg = io.BytesIO()
    img_from_q50.save(buf_png_from_jpg, format="PNG")
    png_from_jpg_bytes = buf_png_from_jpg.getvalue()
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-14-PNG-FROM-JPEG",
            name="PNG with Inherited JPEG Artifacts",
            description="Lossy JPEG Q50 saved into lossless PNG container.",
            construction_method="Encode Q50 JPEG -> decode -> save as PNG bytes",
            intended_test_property="Demonstrates that PNG container can carry inherited 8x8 JPEG blocking artifacts.",
            format_name="PNG",
            pil_image=img_from_q50,
            raw_bytes=png_from_jpg_bytes
        )
    )

    # 15. Tiny Valid Image (Below 8x8 and 3x3 limits)
    img_tiny = Image.new("RGB", (4, 4), color=(200, 100, 50))
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-15-TINY-IMAGE",
            name="Sub-Block Tiny Dimensions (4x4)",
            description="Valid 4x4 image smaller than standard 8x8 block size.",
            construction_method="Image.new('RGB', (4, 4), color=(200, 100, 50))",
            intended_test_property="DCT analysis returns documented UNAVAILABLE status gracefully.",
            format_name="RAW_PIL",
            pil_image=img_tiny
        )
    )

    # 16. Malformed Image Payload
    corrupt_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00TRUNCATED_AND_CORRUPTED"
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-16-MALFORMED-PAYLOAD",
            name="Truncated/Corrupted JPEG Payload",
            description="Starts with valid JPEG magic bytes but contains broken truncated stream.",
            construction_method="JPEG header prefix concatenated with truncated invalid byte sequence",
            intended_test_property="Image validation rejects with HTTP 400 without crashing or unhandled exception.",
            format_name="CORRUPT",
            pil_image=None,
            raw_bytes=corrupt_bytes,
            dimensions=(0, 0)
        )
    )


    # 17. JPEG with Valid Embedded IFD1 Thumbnail and EXIF (Mission 09)
    img_17_main = Image.new("RGB", (128, 128), (140, 70, 70))
    for x in range(20, 60):
        for y in range(20, 60):
            img_17_main.putpixel((x, y), (70, 70, 180))
    img_17_thumb = img_17_main.resize((32, 32), Image.Resampling.BILINEAR)
    buf_17_t = io.BytesIO()
    img_17_thumb.save(buf_17_t, format="JPEG", quality=85)
    t17_bytes = buf_17_t.getvalue()

    import struct
    endian = "<"
    tiff_header = bytes([0x49, 0x49, 0x2a, 0, 8, 0, 0, 0])
    ifd0_entries = struct.pack(f"{endian}HHIHH", 0x0100, 3, 1, 128, 0)
    ifd0_count = struct.pack(f"{endian}H", 1)
    ifd1_offset = 26
    next_ifd0 = struct.pack(f"{endian}I", ifd1_offset)
    thumb_offset = 56
    thumb_len = len(t17_bytes)
    ifd1_count = struct.pack(f"{endian}H", 2)
    entry_thumb_off = struct.pack(f"{endian}HHII", 0x0201, 4, 1, thumb_offset)
    entry_thumb_len = struct.pack(f"{endian}HHII", 0x0202, 4, 1, thumb_len)
    next_ifd1 = struct.pack(f"{endian}I", 0)

    tiff_17 = (
        tiff_header +
        ifd0_count + ifd0_entries + next_ifd0 +
        ifd1_count + entry_thumb_off + entry_thumb_len + next_ifd1 +
        t17_bytes
    )
    exif_17 = bytes([0x45, 0x78, 0x69, 0x66, 0, 0]) + tiff_17
    buf_17_m = io.BytesIO()
    img_17_main.save(buf_17_m, format="JPEG", exif=exif_17)
    raw_17 = buf_17_m.getvalue()
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-17-JPEG-WITH-EXIF-THUMBNAIL",
            name="JPEG with Embedded IFD1 Thumbnail",
            description="JPEG container containing standard EXIF and concordant IFD1 thumbnail stream.",
            construction_method="Synthesized 128x128 image with bilinear downsampled 32x32 IFD1 thumbnail",
            intended_test_property="Thumbnail analysis extracts thumbnail and confirms visual concordance (COMPARABLE).",
            format_name="JPEG",
            pil_image=img_17_main,
            raw_bytes=raw_17,
            dimensions=(128, 128)
        )
    )

    # 18. JPEG with Mismatched Embedded Thumbnail (Mission 09)
    img_18_main = Image.new("RGB", (128, 128), (50, 150, 50))
    img_18_divergent_thumb = Image.new("RGB", (32, 32), (200, 20, 20))  # Completely different red canvas
    buf_18_t = io.BytesIO()
    img_18_divergent_thumb.save(buf_18_t, format="JPEG", quality=85)
    t18_bytes = buf_18_t.getvalue()

    thumb_len_18 = len(t18_bytes)
    entry_thumb_len_18 = struct.pack(f"{endian}HHII", 0x0202, 4, 1, thumb_len_18)
    tiff_18 = (
        tiff_header +
        ifd0_count + ifd0_entries + next_ifd0 +
        ifd1_count + entry_thumb_off + entry_thumb_len_18 + next_ifd1 +
        t18_bytes
    )
    exif_18 = bytes([0x45, 0x78, 0x69, 0x66, 0, 0]) + tiff_18
    buf_18_m = io.BytesIO()
    img_18_main.save(buf_18_m, format="JPEG", exif=exif_18)
    raw_18 = buf_18_m.getvalue()
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-18-JPEG-THUMBNAIL-MISMATCH",
            name="JPEG with Contrasting Embedded Thumbnail",
            description="JPEG container where thumbnail content diverges significantly from primary image.",
            construction_method="Green primary image paired with synthetic red thumbnail stream in IFD1",
            intended_test_property="Thumbnail analysis accurately detects divergence (MISMATCH_OBSERVED).",
            format_name="JPEG",
            pil_image=img_18_main,
            raw_bytes=raw_18,
            dimensions=(128, 128)
        )
    )

    # 19. JPEG with Inconsistent EXIF Dimensions (Mission 09)
    from PIL import ExifTags
    img_19 = Image.new("RGB", (120, 80), (60, 90, 140))
    exif_19_obj = img_19.getexif()
    sub_19 = exif_19_obj.get_ifd(ExifTags.IFD.Exif)
    sub_19[ExifTags.Base.ExifImageWidth] = 240  # Inconsistent 240 vs actual 120
    sub_19[ExifTags.Base.ExifImageHeight] = 160
    buf_19 = io.BytesIO()
    img_19.save(buf_19, format="JPEG", exif=exif_19_obj)
    raw_19 = buf_19.getvalue()
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-19-METADATA-DIM-MISMATCH",
            name="JPEG with Conflicting EXIF Dimension Tags",
            description="JPEG with ExifImageWidth/Height declaring dimensions differing from actual raster.",
            construction_method="120x80 image tagged with 240x160 in ExifImageWidth/ExifImageHeight tags",
            intended_test_property="Container consistency check detects dimension mismatch with benign crop explanation.",
            format_name="JPEG",
            pil_image=img_19,
            raw_bytes=raw_19,
            dimensions=(120, 80)
        )
    )

    # 20. PNG with Text Metadata Chunks (Mission 09)
    from PIL import PngImagePlugin
    img_20 = Image.new("RGB", (96, 96), (100, 100, 150))
    png_info_20 = PngImagePlugin.PngInfo()
    png_info_20.add_text("Software", "Adobe Photoshop 2024")
    png_info_20.add_text("Description", "Controlled evaluation test fixture")
    buf_20 = io.BytesIO()
    img_20.save(buf_20, format="PNG", pnginfo=png_info_20)
    raw_20 = buf_20.getvalue()
    fixtures.append(
        SyntheticFixture(
            fixture_id="FIX-20-PNG-TEXT-CHUNKS",
            name="PNG Container with Text Metadata Chunks",
            description="Lossless PNG carrying standard text chunk metadata headers.",
            construction_method="96x96 PNG image saved with PngInfo text chunks (Software, Description)",
            intended_test_property="Metadata inspector extracts PNG text chunks and identifies software tags.",
            format_name="PNG",
            pil_image=img_20,
            raw_bytes=raw_20,
            dimensions=(96, 96)
        )
    )

    return fixtures

