import base64
import io
import os
import pytest
from PIL import Image
from app.services.ela import ELAError, perform_error_level_analysis


def decode_data_url(data_url: str) -> Image.Image:
    """Helper to decode Base64 PNG data URL back into a PIL Image."""
    assert data_url.startswith("data:image/png;base64,")
    b64_part = data_url.split(",", 1)[1]
    raw_bytes = base64.b64decode(b64_part)
    return Image.open(io.BytesIO(raw_bytes))


def test_ela_valid_jpeg(uniform_image):
    result = perform_error_level_analysis(uniform_image, is_png=False, quality=90, scale_factor=15.0)
    assert result.status == "SUCCESS"
    assert result.metrics is not None
    assert result.heatmap_data_url is not None
    
    # Verify heatmap is decodable PNG and dimensions match input
    heatmap = decode_data_url(result.heatmap_data_url)
    assert heatmap.format == "PNG"
    assert heatmap.size == uniform_image.size
    
    # Metrics checks
    m = result.metrics
    assert m.recompression_quality == 90
    assert m.scale_factor == 15.0
    assert 0.0 <= m.mean_absolute_difference <= 255.0
    assert 0.0 <= m.max_absolute_difference <= 255.0
    assert 0.0 <= m.std_absolute_difference <= 255.0


def test_ela_valid_png():
    img = Image.new("RGBA", (75, 50), color=(100, 150, 200, 255))
    result = perform_error_level_analysis(img, is_png=True, quality=90)
    assert result.status == "SUCCESS"
    assert "lossless PNG" in result.analysis_notes
    
    heatmap = decode_data_url(result.heatmap_data_url)
    assert heatmap.size == (75, 50)


def test_ela_uniform_image_deterministic(uniform_image):
    res1 = perform_error_level_analysis(uniform_image, quality=90, scale_factor=15.0)
    res2 = perform_error_level_analysis(uniform_image, quality=90, scale_factor=15.0)
    
    assert res1.metrics.mean_absolute_difference == res2.metrics.mean_absolute_difference
    assert res1.metrics.max_absolute_difference == res2.metrics.max_absolute_difference
    # For a completely flat uniform color, recompression error is very low
    assert res1.metrics.mean_absolute_difference < 5.0


def test_ela_high_frequency_noise(texture_image):
    result = perform_error_level_analysis(texture_image, quality=90, scale_factor=15.0)
    assert result.status == "SUCCESS"
    # Noisy images should have non-zero variance
    assert result.metrics.mean_absolute_difference > 0.0
    assert result.metrics.max_absolute_difference > 0.0


def test_ela_no_disk_leakage(uniform_image, tmp_path):
    # Verify that performing ELA does not leave temporary files in cwd
    initial_files = set(os.listdir("."))
    _ = perform_error_level_analysis(uniform_image)
    final_files = set(os.listdir("."))
    
    assert initial_files == final_files, f"Leaked files on disk: {final_files - initial_files}"
