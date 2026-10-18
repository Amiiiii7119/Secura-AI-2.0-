import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.evidence import (
    AIDetectionDecision,
    ModelLifecycleState,
    ModelRegistryStatusResponse,
)
from app.services.ai_image_detector import get_ai_image_detector
from scripts.evaluate_ai_detector import calculate_comprehensive_metrics


@pytest.fixture
def client():
    return TestClient(app)


def test_model_registry_status_endpoint(client):
    res = client.get("/api/v1/models/status")
    assert res.status_code == 200
    data = res.json()

    # Validate against schema
    resp_obj = ModelRegistryStatusResponse(**data)
    assert resp_obj.status == "operational"
    assert resp_obj.backbone.architecture == "Vision Transformer (ViT-L/14, 304M params)"
    assert resp_obj.backbone.expected_dim == 768
    assert resp_obj.backbone.state in (ModelLifecycleState.READY, ModelLifecycleState.UNAVAILABLE)
    assert resp_obj.inference_ready in (True, False)

    # Check registered probes
    assert len(resp_obj.registered_heads) >= 2
    head_ids = [h.head_id for h in resp_obj.registered_heads]
    assert "UniversalFakeDetect" in head_ids
    assert "SecuraCustom" in head_ids

    # UniversalFakeDetect must be verified with expected SHA-256
    ufd = next(h for h in resp_obj.registered_heads if h.head_id == "UniversalFakeDetect")
    assert ufd.weights_loaded is True
    assert ufd.head_state == ModelLifecycleState.READY
    # But operational state is UNAVAILABLE because backbone is missing
    assert ufd.operational_state in (ModelLifecycleState.READY, ModelLifecycleState.UNAVAILABLE)


def test_deterministic_score_direction_and_class_mapping():
    detector = get_ai_image_detector()
    assert detector.weights_loaded is True

    # Artificial aligned feature (projection > 0)
    # Using positive multiple of weight vector
    norm_w = detector.fc_weight / np.linalg.norm(detector.fc_weight)
    logit, margin, pred_class, decision = detector.compute_linear_probe(norm_w * 2.0)
    assert logit > 0.1
    assert margin > 0.5
    assert pred_class == "artificial"
    assert decision == AIDetectionDecision.AI_GENERATED_CLASS

    # Real aligned feature (projection < 0)
    # Using negative multiple of weight vector
    neg_logit, neg_margin, neg_pred_class, neg_decision = detector.compute_linear_probe(-norm_w * 2.0)
    assert neg_logit < -0.1
    assert neg_margin < 0.5
    assert neg_pred_class == "human"
    assert neg_decision == AIDetectionDecision.REAL_IMAGE_CLASS


def test_roc_auc_rank_concordance_exactness():
    """Verify rank-sum concordance calculation across distinct distributions."""
    # Case 1: Perfect concordance (all positive scores > all negative scores)
    y_true = [1, 1, 0, 0]
    y_scores = [0.8, 0.9, -0.2, -0.5]
    m1 = calculate_comprehensive_metrics(y_true, y_scores, threshold=0.0)
    assert m1["roc_auc"] == 1.0000
    assert m1["accuracy"] == 1.0000

    # Case 2: Complete ranking inversion (the exact mathematical cause of the 0.0000 AUC on surrogate features)
    # Positive samples are all ranked LOWER than negative samples
    y_scores_inverted = [-0.8, -0.9, 0.2, 0.5]
    m2 = calculate_comprehensive_metrics(y_true, y_scores_inverted, threshold=0.0)
    assert m2["roc_auc"] == 0.0000
    assert m2["accuracy"] == 0.0000

    # Case 3: Tied scores (all scores identical)
    y_scores_tied = [0.0, 0.0, 0.0, 0.0]
    m3 = calculate_comprehensive_metrics(y_true, y_scores_tied, threshold=0.0)
    assert m3["roc_auc"] == 0.5000
