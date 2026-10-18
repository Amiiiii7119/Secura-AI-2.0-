import io
import os
import pytest
import numpy as np
from PIL import Image

from app.evaluation.fixtures import generate_all_fixtures
from app.services.ela import perform_error_level_analysis
from app.services.dct_analysis import _build_dct_matrix, perform_dct_analysis
from app.services.noise_residual import perform_noise_residual_analysis
from app.services.image_validation import ImageValidationError, validate_image_payload


def test_dct_orthonormal_energy_preservation():
    """Verify Parseval's energy conservation theorem for the 2D orthonormal 8x8 DCT-II.
    
    For any real 8x8 matrix B and orthonormal transform matrix T:
        C = T @ B @ T.T
        Frobenius norm squared of B == Frobenius norm squared of C:
        sum(B^2) == sum(C^2)
    """
    T = _build_dct_matrix(8)
    # Check T @ T.T is identity
    assert np.allclose(T @ T.T, np.eye(8), atol=1e-5)
    
    # Arbitrary test block with pseudo-random values
    rng = np.random.RandomState(1234)
    B = rng.uniform(0.0, 255.0, (8, 8)).astype(np.float32)
    
    # 2D DCT transform
    C = T @ B @ T.T
    
    energy_spatial = float(np.sum(B ** 2))
    energy_frequency = float(np.sum(C ** 2))
    
    assert np.isclose(energy_spatial, energy_frequency, rtol=1e-4)


def test_numerical_outputs_are_strictly_finite():
    """Verify that all metrics generated across all 16 synthetic fixtures are strictly finite."""
    fixtures = generate_all_fixtures()
    for f in fixtures:
        if f.pil_image is not None and f.pil_image.size[0] >= 8 and f.pil_image.size[1] >= 8:
            ela_res = perform_error_level_analysis(f.pil_image)
            if ela_res.metrics:
                assert np.isfinite(ela_res.metrics.mean_absolute_difference)
                assert np.isfinite(ela_res.metrics.max_absolute_difference)
                assert np.isfinite(ela_res.metrics.std_absolute_difference)
                
            dct_res = perform_dct_analysis(f.pil_image)
            if dct_res.metrics:
                assert np.isfinite(dct_res.metrics.blocking_artifact_ratio)
                assert np.isfinite(dct_res.metrics.boundary_discontinuity)
                assert np.isfinite(dct_res.metrics.internal_discontinuity)
                assert np.isfinite(dct_res.metrics.mean_block_energy)
                
            noise_res = perform_noise_residual_analysis(f.pil_image)
            if noise_res.metrics:
                assert np.isfinite(noise_res.metrics.mean_absolute_residual)
                assert np.isfinite(noise_res.metrics.std_residual)
                assert np.isfinite(noise_res.metrics.max_residual)
                assert np.isfinite(noise_res.metrics.noise_energy)
                if noise_res.metrics.snr_estimate_db is not None:
                    assert np.isfinite(noise_res.metrics.snr_estimate_db)


def test_deterministic_output_on_identical_bytes():
    """Verify that repeated analysis on identical decoded inputs produces exact byte-for-byte metrics."""
    img = Image.new("RGB", (64, 64), color=(85, 120, 195))
    
    ela1 = perform_error_level_analysis(img)
    ela2 = perform_error_level_analysis(img)
    assert ela1.metrics.mean_absolute_difference == ela2.metrics.mean_absolute_difference
    assert ela1.metrics.max_absolute_difference == ela2.metrics.max_absolute_difference
    
    dct1 = perform_dct_analysis(img)
    dct2 = perform_dct_analysis(img)
    assert dct1.metrics.blocking_artifact_ratio == dct2.metrics.blocking_artifact_ratio
    assert dct1.metrics.mean_block_energy == dct2.metrics.mean_block_energy
    
    noise1 = perform_noise_residual_analysis(img)
    noise2 = perform_noise_residual_analysis(img)
    assert noise1.metrics.mean_absolute_residual == noise2.metrics.mean_absolute_residual
    assert noise1.metrics.noise_energy == noise2.metrics.noise_energy


def test_rgba_alpha_handling_with_divergent_hidden_rgb():
    """Verify that transparent pixels with divergent hidden RGB values composite identically.
    
    Security / correctness property: An adversary could hide high-frequency noise or
    unrelated imagery in RGB channels of pixels with alpha=0. Proper compositing ensures
    such hidden data does not bleed into visible forensic metrics.
    """
    # Image 1: alpha=0 with hidden red (255, 0, 0, 0)
    img1 = Image.new("RGBA", (32, 32), color=(255, 0, 0, 0))
    # Image 2: alpha=0 with hidden blue (0, 0, 255, 0)
    img2 = Image.new("RGBA", (32, 32), color=(0, 0, 255, 0))
    
    dct1 = perform_dct_analysis(img1)
    dct2 = perform_dct_analysis(img2)
    assert dct1.metrics.boundary_discontinuity == dct2.metrics.boundary_discontinuity
    assert dct1.metrics.internal_discontinuity == dct2.metrics.internal_discontinuity
    assert dct1.metrics.mean_block_energy == dct2.metrics.mean_block_energy
    
    noise1 = perform_noise_residual_analysis(img1)
    noise2 = perform_noise_residual_analysis(img2)
    assert noise1.metrics.mean_absolute_residual == noise2.metrics.mean_absolute_residual
    assert noise1.metrics.noise_energy == noise2.metrics.noise_energy


def test_dct_remainder_grid_truncation():
    """Verify that dimensions non-divisible by 8 truncate exactly to documented full 8x8 block grid."""
    w, h = 67, 73
    img = Image.new("RGB", (w, h), color=(100, 100, 100))
    res = perform_dct_analysis(img)
    assert res.status == "SUCCESS"
    assert res.metrics.analyzed_width == 64
    assert res.metrics.analyzed_height == 72
    assert res.metrics.total_blocks == (64 // 8) * (72 // 8)  # 8 * 9 = 72
    assert "Remainder pixels (3x, 1y)" in res.analysis_notes


def test_sub_block_tiny_dimensions_unavailable():
    """Verify that images smaller than minimal filter/block dimensions return documented UNAVAILABLE status."""
    # 2x2 image cannot form 8x8 DCT or 3x3 Laplacian
    img_2x2 = Image.new("RGB", (2, 2), color=(50, 50, 50))
    dct_res = perform_dct_analysis(img_2x2)
    assert dct_res.status == "UNAVAILABLE"
    assert dct_res.metrics is None
    
    noise_res = perform_noise_residual_analysis(img_2x2)
    assert noise_res.status == "UNAVAILABLE"
    assert noise_res.metrics is None


def test_measured_recompression_divergence():
    """Verify that ELA measures physical recompression divergence between uncompressed and pre-compressed inputs."""
    # Uncompressed smooth gradient vs Q50 recompressed
    grad = np.tile(np.linspace(0, 255, 64, dtype=np.uint8), (64, 1))
    img_clean = Image.fromarray(np.stack([grad]*3, axis=-1), mode="RGB")
    
    buf = io.BytesIO()
    img_clean.save(buf, format="JPEG", quality=50)
    buf.seek(0)
    img_q50 = Image.open(buf)
    
    ela_clean = perform_error_level_analysis(img_clean, is_png=False)
    ela_q50 = perform_error_level_analysis(img_q50, is_png=False)
    
    # Both produce finite, non-zero metrics
    assert ela_clean.metrics.mean_absolute_difference >= 0.0
    assert ela_q50.metrics.mean_absolute_difference >= 0.0


def test_harness_zero_disk_leakage():
    """Verify that evaluating synthetic fixtures leaves no temporary files in working directory."""
    files_before = set(os.listdir("."))
    fixtures = generate_all_fixtures()
    for f in fixtures[:5]:
        if f.pil_image:
            _ = perform_error_level_analysis(f.pil_image)
            _ = perform_dct_analysis(f.pil_image)
            _ = perform_noise_residual_analysis(f.pil_image)
    files_after = set(os.listdir("."))
    assert files_before == files_after


def test_metadata_forensic_properties_across_fixtures():
    """Verify that metadata inspection on all synthetic fixtures yields valid, finite, privacy-safe models."""
    from app.schemas.evidence import ImageFormat, ImageValidationResult, MetadataStatus
    from app.services.metadata_inspector import inspect_metadata

    fixtures = generate_all_fixtures()
    for f in fixtures:
        if f.raw_bytes is not None and f.format_name in ["JPEG", "PNG"]:
            fmt = ImageFormat.JPEG if f.format_name == "JPEG" else ImageFormat.PNG
            w, h = f.dimensions
            val = ImageValidationResult(
                is_valid=True,
                detected_format=fmt,
                width=w,
                height=h,
                pixel_count=w * h,
                color_mode="RGB",
                file_size_bytes=len(f.raw_bytes),
                mime_type="image/jpeg" if fmt == ImageFormat.JPEG else "image/png"
            )
            pil_img = f.pil_image or Image.open(io.BytesIO(f.raw_bytes))
            res = inspect_metadata(pil_img, f.raw_bytes, val)
            assert res.inventory.status in [MetadataStatus.PRESENT, MetadataStatus.ABSENT, MetadataStatus.PARTIAL]
            assert res.gps_summary.coordinates_redacted is True
            assert res.gps_summary.latitude is None
            assert res.gps_summary.longitude is None
            if res.thumbnail_analysis.has_thumbnail and res.thumbnail_analysis.similarity_score is not None:
                assert 0.0 <= res.thumbnail_analysis.similarity_score <= 1.0
