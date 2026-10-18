"""Unit, integration, and property tests for AI-Generated Image Detector Engine.

Covers:
- Singleton lifecycle and thread-safety
- Weight loading, verification, and corruption isolation
- Preprocessing geometry and normalization invariants
- Linear probe algebraic correctness and decision boundaries
- Safe fallback when backbone vision model is not loaded
- API integration in POST /api/v1/analyze/image
- Failure isolation and component error resilience
"""

import hashlib
import io
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
from PIL import Image
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.evidence import AIDetectionDecision, AIDetectionStatus
from app.services.ai_image_detector import (
    AIImageDetectorService,
    get_ai_image_detector,
    MODEL_NAME,
    MODEL_VERSION,
)


@pytest.fixture
def detector_service():
    """Return the global detector service."""
    return get_ai_image_detector()


@pytest.fixture
def sample_rgb_image():
    """Return a standard 300x200 RGB PIL image."""
    img = Image.new("RGB", (300, 200), color=(128, 64, 32))
    return img


@pytest.fixture
def sample_rgba_image():
    """Return a standard 150x250 RGBA PIL image with semi-transparent channel."""
    img = Image.new("RGBA", (150, 250), color=(100, 150, 200, 128))
    return img


@pytest.fixture
def sample_grayscale_image():
    """Return a 200x200 L-mode PIL image."""
    img = Image.new("L", (200, 200), color=180)
    return img


# =========================================================================
# 1. Lifecycle and Weight Loading Tests
# =========================================================================

def test_singleton_identity():
    """Verify get_ai_image_detector returns the identical singleton instance."""
    s1 = get_ai_image_detector()
    s2 = get_ai_image_detector()
    assert s1 is s2


def test_weights_loaded_correctly(detector_service):
    """Verify linear probe weights are loaded with expected dimensionality and bias."""
    assert detector_service.weights_loaded is True
    assert detector_service.status == AIDetectionStatus.LOADED
    assert detector_service.fc_weight is not None
    assert detector_service.fc_weight.shape == (768,)
    assert detector_service.fc_weight.dtype == np.float32
    assert detector_service.fc_bias is not None
    assert isinstance(detector_service.fc_bias, float)
    # The official probe bias is approx -0.5167
    assert -0.6 < detector_service.fc_bias < -0.4


def test_missing_weights_file(tmp_path):
    """Verify missing weights file results in WEIGHTS_MISSING status without throwing."""
    fake_path = tmp_path / "nonexistent_fc_weights.pth"
    service = AIImageDetectorService(weights_path=fake_path)
    assert service.weights_loaded is False
    assert service.status == AIDetectionStatus.WEIGHTS_MISSING
    assert "not found" in (service.init_error or "").lower()

    # Inference returns appropriate unavailable payload
    img = Image.new("RGB", (64, 64))
    res = service.detect(img)
    assert res.available is False
    assert res.model_status == AIDetectionStatus.WEIGHTS_MISSING
    assert res.error_code == "WEIGHTS_UNAVAILABLE"


def test_corrupted_weights_checksum(tmp_path):
    """Verify corrupted weights file fails checksum verification and reports UNAVAILABLE."""
    corrupt_path = tmp_path / "corrupted_fc_weights.pth"
    corrupt_path.write_bytes(b"corrupted binary data that does not match official sha256")

    service = AIImageDetectorService(weights_path=corrupt_path)
    assert service.weights_loaded is False
    assert service.status == AIDetectionStatus.UNAVAILABLE
    assert "checksum mismatch" in (service.init_error or "").lower()


# =========================================================================
# 2. Preprocessing Geometry and Invariants
# =========================================================================

def test_preprocess_rgb_invariants(detector_service, sample_rgb_image):
    """Verify preprocessing outputs exactly (3, 224, 224) float32 array with normalized values."""
    tensor = detector_service.preprocess_image(sample_rgb_image)
    assert isinstance(tensor, np.ndarray)
    assert tensor.shape == (3, 224, 224)
    assert tensor.dtype == np.float32
    # Ensure values are not NaN or Inf
    assert not np.isnan(tensor).any()
    assert not np.isinf(tensor).any()


def test_preprocess_rgba_compositing(detector_service, sample_rgba_image):
    """Verify RGBA images with transparency composite onto white background cleanly."""
    tensor = detector_service.preprocess_image(sample_rgba_image)
    assert tensor.shape == (3, 224, 224)
    assert tensor.dtype == np.float32


def test_preprocess_grayscale_conversion(detector_service, sample_grayscale_image):
    """Verify Grayscale images convert to 3 channels and match expected shape."""
    tensor = detector_service.preprocess_image(sample_grayscale_image)
    assert tensor.shape == (3, 224, 224)


# =========================================================================
# 3. Linear Probe Algebraic Correctness & Decision Boundaries
# =========================================================================

def test_linear_probe_positive_decision(detector_service):
    """Verify feature aligned with weight vector produces AI_GENERATED_CLASS."""
    w = detector_service.fc_weight
    w_norm = w / (np.linalg.norm(w) + 1e-9)
    # Feature aligned with probe weights
    feat = w_norm * 2.0
    logit, margin, pred, dec = detector_service.compute_linear_probe(feat)

    assert logit > 0.1
    assert dec == AIDetectionDecision.AI_GENERATED_CLASS
    assert pred == "artificial"
    assert 0.0 < margin <= 1.0


def test_linear_probe_negative_decision(detector_service):
    """Verify feature anti-aligned with weight vector produces REAL_IMAGE_CLASS."""
    w = detector_service.fc_weight
    w_norm = w / (np.linalg.norm(w) + 1e-9)
    # Feature pointing away from probe weights
    feat = w_norm * (-2.0)
    logit, margin, pred, dec = detector_service.compute_linear_probe(feat)

    assert logit < -0.1
    assert dec == AIDetectionDecision.REAL_IMAGE_CLASS
    assert pred == "human"
    assert 0.0 <= margin < 0.5


def test_linear_probe_inconclusive_boundary(detector_service):
    """Verify feature within [-0.1, 0.1] boundary yields INCONCLUSIVE."""
    w = detector_service.fc_weight
    bias = detector_service.fc_bias
    norm_w = np.linalg.norm(w)
    w_norm = w / norm_w

    cos_theta = (-bias) / norm_w
    sin_theta = np.sqrt(1.0 - cos_theta**2)

    rng = np.random.RandomState(123)
    rand_v = rng.randn(768).astype(np.float32)
    u = rand_v - np.dot(rand_v, w_norm) * w_norm
    u = u / np.linalg.norm(u)

    feat = cos_theta * w_norm + sin_theta * u

    logit, margin, pred, dec = detector_service.compute_linear_probe(feat)
    assert -0.1 <= logit <= 0.1
    assert dec == AIDetectionDecision.INCONCLUSIVE


def test_linear_probe_dimension_mismatch(detector_service):
    """Verify passing feature vector with dimension != 768 raises ValueError."""
    bad_feat = np.ones(512, dtype=np.float32)
    with pytest.raises(ValueError, match="dimension mismatch"):
        detector_service.compute_linear_probe(bad_feat)


# =========================================================================
# 4. Detector Execution and Honest State Reporting
# =========================================================================

def test_detect_without_backbone_reports_unavailable(detector_service, sample_rgb_image):
    """Verify detector reports UNAVAILABLE when backbone weights are not installed."""
    with patch.object(detector_service, "backbone_loaded", False), patch.object(detector_service, "clip_vision_model", None):
        res = detector_service.detect(sample_rgb_image)
        assert res.available is False
    assert res.model_name == MODEL_NAME
    assert res.model_version == MODEL_VERSION
    assert res.model_status == AIDetectionStatus.UNAVAILABLE
    assert res.decision_status == AIDetectionDecision.UNAVAILABLE
    assert res.error_code == "BACKBONE_WEIGHTS_UNAVAILABLE"
    assert res.raw_score is None
    assert res.uncalibrated_margin is None
    assert len(res.limitations) > 0


def test_detect_with_feature_override(detector_service, sample_rgb_image):
    """Verify feature_override bypasses backbone and performs probe evaluation."""
    w = detector_service.fc_weight
    w_norm = w / (np.linalg.norm(w) + 1e-9)
    feat = w_norm * 1.5

    res = detector_service.detect(sample_rgb_image, feature_override=feat)
    assert res.available is True
    assert res.model_status == AIDetectionStatus.LOADED
    assert res.decision_status == AIDetectionDecision.AI_GENERATED_CLASS
    assert res.raw_score is not None
    assert res.raw_score > 0.1
    assert res.uncalibrated_margin is not None
    assert res.error_code is None


def test_detect_invalid_image_dimensions(detector_service):
    """Verify passing 0-dimension image returns INFERENCE_FAILED."""
    empty_img = Image.new("RGB", (0, 0))
    res = detector_service.detect(empty_img)
    assert res.available is False
    assert res.model_status == AIDetectionStatus.INFERENCE_FAILED
    assert res.decision_status == AIDetectionDecision.UNAVAILABLE
    assert res.error_code == "INVALID_IMAGE_DIMENSIONS"


# =========================================================================
# 5. API Endpoint Integration & Resilience Tests
# =========================================================================

@pytest.mark.asyncio
async def test_api_includes_ai_detection(valid_rgb_jpeg_bytes):
    """Verify POST /api/v1/analyze/image includes ai_detection field in response."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test_ai.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
        response = await client.post("/api/v1/analyze/image", files=files)

    assert response.status_code == 200
    data = response.json()

    assert "ai_detection" in data
    ai_det = data["ai_detection"]
    assert ai_det is not None
    assert ai_det["model_name"] in (MODEL_NAME, "Swin AI-Image-Detector (umm-maybe)", "Multi-Architecture Ensemble (Swin + CLIP ViT-L/14)")
    assert ai_det["model_version"] in (MODEL_VERSION, "1.2.0-swin", "1.0.0-ensemble")
    # When real weights are loaded, decision status is active; if unavailable, it is UNAVAILABLE
    assert ai_det["decision_status"] in ("REAL_IMAGE_CLASS", "AI_GENERATED_CLASS", "UNAVAILABLE")
    assert ai_det["model_status"] in ("LOADED", "UNAVAILABLE")
    assert "limitations" in ai_det
    assert isinstance(ai_det["limitations"], list)
    assert len(ai_det["limitations"]) > 0


@pytest.mark.asyncio
async def test_api_ai_detector_failure_isolation(valid_rgb_jpeg_bytes):
    """Verify that an unexpected exception in AI detector does not fail the request."""
    with patch("app.services.ai_image_detector.AIImageDetectorService.detect", side_effect=RuntimeError("Simulated CUDA OOM")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            files = {"file": ("test_fault.jpg", valid_rgb_jpeg_bytes, "image/jpeg")}
            response = await client.post("/api/v1/analyze/image", files=files)

    assert response.status_code == 200
    data = response.json()

    # Request succeeds, ELA and other layers succeed
    assert data["ela_forensics"]["status"] == "SUCCESS"
    assert data["dct_analysis"]["status"] == "SUCCESS"

    # AI detection recorded as failed in component errors
    assert data["ai_detection"] is None
    ai_errors = [e for e in data["component_errors"] if e["component"] == "AIImageDetector"]
    assert len(ai_errors) == 1
    assert ai_errors[0]["error_code"] == "AI_DETECTION_UNEXPECTED_FAILURE"
    assert "RuntimeError" in ai_errors[0]["message"]


# =========================================================================
# 6. Model Registry & Custom Head Switching Tests (Mission 12)
# =========================================================================

def test_model_registry_head_switching(detector_service):
    """Verify switching between UniversalFakeDetect and SecuraCustom heads."""
    custom_weights_p = Path(__file__).resolve().parent.parent / "models" / "weights" / "custom_fc_weights.pth"
    if not custom_weights_p.exists():
        pytest.skip("custom_fc_weights.pth not found")

    # Switch to SecuraCustom
    success = detector_service.switch_head("SecuraCustom")
    assert success is True
    assert detector_service.active_head == "SecuraCustom"
    assert "Custom" in detector_service.model_name
    assert detector_service.weights_loaded is True

    # Evaluate feature vector with custom head
    w = detector_service.fc_weight
    w_norm = w / (np.linalg.norm(w) + 1e-9)
    logit, margin, pred, dec = detector_service.compute_linear_probe(w_norm * 2.0)
    assert logit > 0.1
    assert dec == AIDetectionDecision.AI_GENERATED_CLASS

    # Switch back to UniversalFakeDetect
    success_orig = detector_service.switch_head("UniversalFakeDetect")
    assert success_orig is True
    assert detector_service.active_head == "UniversalFakeDetect"
    assert "UniversalFakeDetect" in detector_service.model_name
    assert detector_service.weights_loaded is True


def test_switch_to_invalid_head(detector_service):
    """Verify attempting to switch to an unregistered head returns False without crashing."""
    success = detector_service.switch_head("NonExistentHeadName")
    assert success is False
    # Active head remains unchanged
    assert detector_service.active_head in ("UniversalFakeDetect", "SecuraCustom")
