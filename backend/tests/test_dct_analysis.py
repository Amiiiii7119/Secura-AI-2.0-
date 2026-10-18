import base64
import io
import os
import pytest
import numpy as np
from PIL import Image

from app.services.dct_analysis import DCTAnalysisError, perform_dct_analysis


def decode_png_data_url(data_url: str) -> Image.Image:
    assert data_url.startswith("data:image/png;base64,")
    raw = base64.b64decode(data_url.split(",", 1)[1])
    return Image.open(io.BytesIO(raw))


def test_dct_valid_rgb_jpeg(uniform_image):
    result = perform_dct_analysis(uniform_image)
    assert result.status == "SUCCESS"
    assert result.metrics is not None
    assert result.visualization_data_url is not None
    
    m = result.metrics
    assert m.block_size == 8
    assert m.analyzed_width == 64
    assert m.analyzed_height == 64
    assert m.total_blocks == 64
    assert 0.0 <= m.boundary_discontinuity <= 255.0
    assert 0.0 <= m.internal_discontinuity <= 255.0
    assert np.isfinite(m.blocking_artifact_ratio)
    assert np.isfinite(m.mean_block_energy)
    
    vis = decode_png_data_url(result.visualization_data_url)
    assert vis.size == (64, 64)


def test_dct_valid_rgb_png():
    img = Image.new("RGB", (32, 32), color=(50, 100, 150))
    result = perform_dct_analysis(img)
    assert result.status == "SUCCESS"
    assert result.metrics.total_blocks == 16


def test_dct_dimensions_not_divisible_by_eight():
    # 25x30 image -> 24x24 analyzed grid (3x3 blocks = 9 blocks)
    img = Image.new("RGB", (25, 30), color=(120, 80, 40))
    result = perform_dct_analysis(img)
    assert result.status == "SUCCESS"
    assert result.metrics.analyzed_width == 24
    assert result.metrics.analyzed_height == 24
    assert result.metrics.total_blocks == 9
    assert "Remainder pixels (1x, 6y)" in result.analysis_notes


def test_dct_small_dimensions_unavailable():
    # 6x6 image cannot form an 8x8 block
    img = Image.new("RGB", (6, 6), color=(200, 200, 200))
    result = perform_dct_analysis(img)
    assert result.status == "UNAVAILABLE"
    assert result.metrics is None
    assert result.visualization_data_url is None
    assert "smaller than the minimum 8x8" in result.analysis_notes


def test_dct_grayscale_input():
    img = Image.new("L", (16, 16), color=128)
    result = perform_dct_analysis(img)
    assert result.status == "SUCCESS"
    assert result.metrics.total_blocks == 4


def test_dct_rgba_input_with_transparency():
    img = Image.new("RGBA", (16, 16), color=(255, 0, 0, 0))  # Fully transparent red
    result = perform_dct_analysis(img)
    assert result.status == "SUCCESS"
    # Should composite onto white, resulting in pure white luminance (flat)
    assert result.metrics.boundary_discontinuity == 0.0


def test_dct_deterministic_output(texture_image):
    res1 = perform_dct_analysis(texture_image)
    res2 = perform_dct_analysis(texture_image)
    assert res1.metrics.blocking_artifact_ratio == res2.metrics.blocking_artifact_ratio
    assert res1.metrics.mean_block_energy == res2.metrics.mean_block_energy


def test_dct_synthetic_high_frequency_noise(texture_image):
    result = perform_dct_analysis(texture_image)
    assert result.status == "SUCCESS"
    assert result.metrics.mean_block_energy > 0.0
    assert np.isfinite(result.metrics.blocking_artifact_ratio)


def test_dct_no_disk_leakage(uniform_image):
    files_before = set(os.listdir("."))
    _ = perform_dct_analysis(uniform_image)
    files_after = set(os.listdir("."))
    assert files_before == files_after
