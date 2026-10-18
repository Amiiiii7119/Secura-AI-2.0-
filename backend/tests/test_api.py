import io
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from app.main import app
from app.core.config import settings
from app.services.ela import ELAError
from app.services.dct_analysis import DCTAnalysisError
from app.services.noise_residual import NoiseResidualError


@pytest.mark.asyncio
async def test_api_analyze_valid_jpeg(valid_rgb_jpeg_bytes):
    """Test full analysis pipeline with a valid JPEG image."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
        response = await client.post("/api/v1/analyze/image", files=files)
        
    assert response.status_code == 200
    data = response.json()
    
    assert "request_id" in data
    assert "timestamp_utc" in data
    assert data["image_validation"]["is_valid"] is True
    assert data["image_validation"]["detected_format"] == "JPEG"
    assert data["image_validation"]["width"] == 100
    assert data["image_validation"]["height"] == 100
    
    # ELA checks
    assert data["ela_forensics"] is not None
    assert data["ela_forensics"]["status"] == "SUCCESS"
    assert data["ela_forensics"]["heatmap_data_url"].startswith("data:image/png;base64,")
    
    # DCT checks
    assert data["dct_analysis"] is not None
    assert data["dct_analysis"]["status"] == "SUCCESS"
    assert data["dct_analysis"]["metrics"]["total_blocks"] == 144  # (96//8) * (96//8) = 12*12 = 144
    assert data["dct_analysis"]["visualization_data_url"].startswith("data:image/png;base64,")
    
    # Noise Residual checks
    assert data["noise_residual"] is not None
    assert data["noise_residual"]["status"] == "SUCCESS"
    assert data["noise_residual"]["metrics"]["mean_absolute_residual"] >= 0.0
    assert data["noise_residual"]["visualization_data_url"].startswith("data:image/png;base64,")
    
    # C2PA checks
    assert data["c2pa_provenance"]["status"] == "C2PA_MISSING"
    assert data["c2pa_provenance"]["manifest_present"] is False
    
    # Disclaimer check
    assert "DISCLAIMER" in data["disclaimer"]
    
    # Verify no local filesystem paths are leaked
    resp_str = str(data).lower()
    for leak in ["d:\\", "c:\\", "c:/", "d:/", "users\\", ".venv"]:
        assert leak not in resp_str


@pytest.mark.asyncio
async def test_api_analyze_valid_png(valid_rgb_png_bytes):
    """Test full analysis pipeline with a valid PNG image."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test.png", valid_rgb_png_bytes, "image/png")}
        response = await client.post("/api/v1/analyze/image", files=files)
        
    assert response.status_code == 200
    data = response.json()
    assert data["image_validation"]["detected_format"] == "PNG"
    assert data["ela_forensics"]["status"] == "SUCCESS"
    assert data["dct_analysis"]["status"] == "SUCCESS"
    assert data["noise_residual"]["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_api_analyze_missing_file():
    """Test submitting request with empty files payload."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/analyze/image", files={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_analyze_empty_file():
    """Test submitting a 0-byte file."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("empty.jpg", b"", "image/jpeg")}
        response = await client.post("/api/v1/analyze/image", files=files)
    assert response.status_code == 400
    data = response.json()
    assert "EMPTY_FILE" in str(data)


@pytest.mark.asyncio
async def test_api_analyze_unsupported_format(unsupported_format_bytes):
    """Test submitting an unsupported image format (e.g. BMP)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test.bmp", unsupported_format_bytes, "image/bmp")}
        response = await client.post("/api/v1/analyze/image", files=files)
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_api_analyze_oversized_file():
    """Test upload exceeding MAX_UPLOAD_SIZE_BYTES returns 413."""
    large_payload = b"x" * (settings.MAX_UPLOAD_SIZE_BYTES + 1024)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("large.jpg", large_payload, "image/jpeg")}
        response = await client.post("/api/v1/analyze/image", files=files)
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_api_analyze_controlled_ela_failure(valid_rgb_jpeg_bytes):
    """Test that an internal ELA failure is logged in component_errors without fabricating success."""
    with patch("app.api.routes.perform_error_level_analysis") as mock_ela:
        mock_ela.side_effect = ELAError("Simulated numerical failure in ELA matrix operation")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("test.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
            response = await client.post("/api/v1/analyze/image", files=files)
            
    assert response.status_code == 200
    data = response.json()
    assert data["ela_forensics"] is None
    assert len(data["component_errors"]) > 0
    assert any(err["component"] == "ErrorLevelAnalysis" for err in data["component_errors"])
    # Other components continue to succeed
    assert data["dct_analysis"] is not None
    assert data["noise_residual"] is not None


@pytest.mark.asyncio
async def test_api_analyze_controlled_dct_failure(valid_rgb_jpeg_bytes):
    """Test that an internal DCT failure is recorded in component_errors gracefully."""
    with patch("app.api.routes.perform_dct_analysis") as mock_dct:
        mock_dct.side_effect = DCTAnalysisError("Simulated DCT matrix fault")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("test.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
            response = await client.post("/api/v1/analyze/image", files=files)
            
    assert response.status_code == 200
    data = response.json()
    assert data["dct_analysis"] is None
    assert any(err["component"] == "DCTAnalysis" for err in data["component_errors"])


@pytest.mark.asyncio
async def test_api_analyze_controlled_noise_failure(valid_rgb_jpeg_bytes):
    """Test that an internal Noise Residual failure is recorded in component_errors gracefully."""
    with patch("app.api.routes.perform_noise_residual_analysis") as mock_noise:
        mock_noise.side_effect = NoiseResidualError("Simulated noise residual filtering fault")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("test.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
            response = await client.post("/api/v1/analyze/image", files=files)
            
    assert response.status_code == 200
    data = response.json()
    assert data["noise_residual"] is None
    assert any(err["component"] == "NoiseResidualAnalysis" for err in data["component_errors"])


@pytest.mark.asyncio
async def test_api_analyze_metadata_forensics_section(valid_rgb_jpeg_bytes):
    """Test that metadata_forensics section is populated and structured according to schema."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
        response = await client.post("/api/v1/analyze/image", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "metadata_forensics" in data
    assert data["metadata_forensics"] is not None
    mf = data["metadata_forensics"]
    assert "inventory" in mf
    assert "gps_summary" in mf
    assert "thumbnail_analysis" in mf
    assert "container_consistency" in mf
    assert "analysis_notes" in mf


@pytest.mark.asyncio
async def test_api_analyze_metadata_gps_privacy_enforced(valid_rgb_jpeg_bytes):
    """Test that GPS coordinates are never leaked in the API JSON response."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
        response = await client.post("/api/v1/analyze/image", files=files)

    assert response.status_code == 200
    data = response.json()
    gps = data["metadata_forensics"]["gps_summary"]
    assert gps["coordinates_redacted"] is True
    assert gps["latitude"] is None
    assert gps["longitude"] is None


@pytest.mark.asyncio
async def test_api_analyze_controlled_metadata_failure(valid_rgb_jpeg_bytes):
    """Test that a metadata extraction failure does not crash the forensic pipeline."""
    with patch("app.api.routes.inspect_metadata") as mock_meta:
        mock_meta.side_effect = RuntimeError("Simulated metadata parser crash")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("test.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
            response = await client.post("/api/v1/analyze/image", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["metadata_forensics"] is None
    assert any(err["component"] == "MetadataInspector" for err in data["component_errors"])
    # Other engines still succeed
    assert data["ela_forensics"] is not None
    assert data["dct_analysis"] is not None
    assert data["noise_residual"] is not None


@pytest.mark.asyncio
async def test_api_analyze_unified_report_present(valid_rgb_jpeg_bytes):
    """Test that unified_report section is populated and structured according to schema."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
        response = await client.post("/api/v1/analyze/image", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "unified_report" in data
    assert data["unified_report"] is not None
    ur = data["unified_report"]
    assert ur["report_schema_version"] == "1.0.0"
    assert ur["analysis_completion_status"] in ["COMPLETE", "PARTIAL_SUCCESS"]
    assert ur["total_findings_count"] in (7, 8)
    assert len(ur["findings"]) in (7, 8)
    assert "findings_by_category" in ur
    assert "cautious_summary" in ur
    assert len(ur["global_limitations"]) == 5


@pytest.mark.asyncio
async def test_api_analyze_controlled_fusion_failure(valid_rgb_jpeg_bytes):
    """Test that an internal fusion service failure is isolated and does not abort the response."""
    with patch("app.api.routes.synthesize_forensic_evidence") as mock_fusion:
        mock_fusion.side_effect = RuntimeError("Simulated fusion consolidation crash")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("test.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
            response = await client.post("/api/v1/analyze/image", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["unified_report"] is None
    assert any(err["component"] == "EvidenceFusion" for err in data["component_errors"])
    # All other forensic components succeed
    assert data["ela_forensics"] is not None
    assert data["dct_analysis"] is not None
    assert data["noise_residual"] is not None
    assert data["metadata_forensics"] is not None
