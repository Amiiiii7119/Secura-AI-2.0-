import base64
import io
import os
import pytest
import numpy as np
from PIL import Image

from app.services.noise_residual import NoiseResidualError, perform_noise_residual_analysis


def decode_png_data_url(data_url: str) -> Image.Image:
    assert data_url.startswith("data:image/png;base64,")
    raw = base64.b64decode(data_url.split(",", 1)[1])
    return Image.open(io.BytesIO(raw))


def test_noise_valid_rgb_jpeg(uniform_image):
    result = perform_noise_residual_analysis(uniform_image)
    assert result.status == "SUCCESS"
    assert result.metrics is not None
    assert result.visualization_data_url is not None
    
    m = result.metrics
    assert "3x3 Discrete Laplacian" in m.filter_type
    assert m.mean_absolute_residual == 0.0  # Flat uniform has zero Laplacian residual
    assert m.std_residual == 0.0
    assert m.max_residual == 0.0
    assert m.noise_energy == 0.0
    
    vis = decode_png_data_url(result.visualization_data_url)
    assert vis.size == uniform_image.size


def test_noise_valid_rgb_png():
    img = Image.new("RGB", (40, 40), color=(120, 140, 160))
    result = perform_noise_residual_analysis(img)
    assert result.status == "SUCCESS"


def test_noise_grayscale_input():
    img = Image.new("L", (30, 30), color=100)
    result = perform_noise_residual_analysis(img)
    assert result.status == "SUCCESS"
    assert result.metrics.mean_absolute_residual == 0.0


def test_noise_rgba_input_with_transparency():
    # Fully transparent canvas with red values
    img = Image.new("RGBA", (25, 25), color=(255, 0, 0, 0))
    result = perform_noise_residual_analysis(img)
    assert result.status == "SUCCESS"
    # Composited onto white -> flat white -> 0 residual
    assert result.metrics.mean_absolute_residual == 0.0


def test_noise_small_dimensions_unavailable():
    # 2x2 image cannot apply 3x3 filter
    img = Image.new("RGB", (2, 2), color=(100, 100, 100))
    result = perform_noise_residual_analysis(img)
    assert result.status == "UNAVAILABLE"
    assert result.metrics is None
    assert result.visualization_data_url is None
    assert "smaller than the minimum 3x3" in result.analysis_notes


def test_noise_synthetic_high_frequency_texture(texture_image):
    result = perform_noise_residual_analysis(texture_image)
    assert result.status == "SUCCESS"
    assert result.metrics.mean_absolute_residual > 0.0
    assert result.metrics.std_residual > 0.0
    assert result.metrics.noise_energy > 0.0
    assert np.isfinite(result.metrics.noise_energy)
    if result.metrics.snr_estimate_db is not None:
        assert np.isfinite(result.metrics.snr_estimate_db)


def test_noise_deterministic_output(texture_image):
    res1 = perform_noise_residual_analysis(texture_image)
    res2 = perform_noise_residual_analysis(texture_image)
    assert res1.metrics.mean_absolute_residual == res2.metrics.mean_absolute_residual
    assert res1.metrics.std_residual == res2.metrics.std_residual


def test_noise_no_disk_leakage(uniform_image):
    files_before = set(os.listdir("."))
    _ = perform_noise_residual_analysis(uniform_image)
    files_after = set(os.listdir("."))
    assert files_before == files_after
