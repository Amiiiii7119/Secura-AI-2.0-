import io
import pytest
from unittest.mock import MagicMock, patch
from app.schemas.evidence import C2PAStatus
from app.services.c2pa_inspector import inspect_c2pa_manifest, SDK_AVAILABLE


def test_c2pa_missing_manifest(valid_rgb_jpeg_bytes):
    """Test standard image without manifest produces C2PA_MISSING status."""
    result = inspect_c2pa_manifest(valid_rgb_jpeg_bytes, mime_type="image/jpeg")
    
    assert result.sdk_available is True
    assert result.status == C2PAStatus.C2PA_MISSING
    assert result.manifest_present is False
    assert result.manifest_data is None
    assert "No C2PA provenance manifest" in result.provenance_notes


def test_c2pa_sdk_unavailable_behavior(valid_rgb_jpeg_bytes):
    """Test fallback when SDK is unavailable or unimportable."""
    with patch("app.services.c2pa_inspector.SDK_AVAILABLE", False):
        result = inspect_c2pa_manifest(valid_rgb_jpeg_bytes, mime_type="image/jpeg")
        assert result.status == C2PAStatus.C2PA_UNAVAILABLE
        assert result.sdk_available is False
        assert result.manifest_present is False
        assert "not available" in result.provenance_notes.lower()


def test_c2pa_manifest_present_mocked_inspection():
    """Test manifest extraction logic when reader detects manifest structures."""
    fake_json = """{
        "active_manifest": {
            "title": "sample_provenance.jpg",
            "claim_generator": "SecuraTestEngine/1.0",
            "format": "image/jpeg",
            "instance_id": "urn:uuid:12345-6789",
            "thumbnail": "data:image/jpeg;base64,123",
            "ingredients": [{"title": "ingredient1"}],
            "assertions": [{"label": "c2pa.actions", "data": {"actions": [{"action": "c2pa.created"}]}}]
        }
    }"""
    mock_reader = MagicMock()
    mock_reader.is_valid.return_value = True
    mock_reader.get_validation_state.return_value = "Valid"
    mock_reader.json.return_value = fake_json

    with patch("c2pa.Reader.try_create", return_value=mock_reader):
        result = inspect_c2pa_manifest(b"dummy_bytes", mime_type="image/jpeg")
        assert result.status == C2PAStatus.C2PA_PRESENT_AND_VALID
        assert result.manifest_present is True
        assert result.claims is not None
        assert result.claims.title == "sample_provenance.jpg"
        assert result.claims.claim_generator == "SecuraTestEngine/1.0"
        assert result.claims.thumbnail_present is True
        assert result.claims.ingredients_count == 1
        assert len(result.claims.assertions) == 1
        mock_reader.close.assert_called_once()


def test_c2pa_manifest_present_with_validation_issues():
    """Test manifest detection when cryptographic signature is invalid."""
    fake_json = """{"active_manifest": {"title": "tampered.jpg"}}"""
    mock_reader = MagicMock()
    mock_reader.is_valid.return_value = False
    mock_reader.get_validation_state.return_value = "InvalidSignature"
    mock_reader.json.return_value = fake_json

    with patch("c2pa.Reader.try_create", return_value=mock_reader):
        result = inspect_c2pa_manifest(b"dummy_bytes", mime_type="image/jpeg")
        assert result.status == C2PAStatus.C2PA_PRESENT_WITH_VALIDATION_ISSUES
        assert result.manifest_present is True
        assert result.claims.title == "tampered.jpg"


def test_c2pa_reader_exception_handling():
    """Test graceful handling when try_create raises an unhandled exception."""
    with patch("c2pa.Reader.try_create", side_effect=RuntimeError("Corrupt JUMBF box")):
        result = inspect_c2pa_manifest(b"dummy_bytes", mime_type="image/jpeg")
        assert result.status == C2PAStatus.C2PA_INSPECTION_ERROR
        assert result.manifest_present is False
        assert "internal parser error" in result.provenance_notes


def test_c2pa_real_signed_vectors_documentation():
    """Document that external cryptographically signed C2PA test vectors are not included
    in this local repository fixture set to avoid bundling third-party signed binaries.
    
    Milestone 1 requirement: Do not invent fake valid C2PA signatures or pass mocked
    verification as real cryptographic validation.
    """
    assert True
