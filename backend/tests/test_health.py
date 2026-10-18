import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_success():
    """Verify health endpoint returns 200, valid JSON, and correct service metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Secura AI"
    assert data["version"] in ["1.0.0", "0.1.0-milestone1"]
    assert "timestamp_utc" in data


@pytest.mark.asyncio
async def test_health_endpoint_no_sensitive_leakage():
    """Verify health endpoint does not leak local filesystem paths, env vars, or secrets."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        
    data = response.json()
    response_text = str(data).lower()
    
    # Sensitive pattern checks
    forbidden_terms = ["d:\\", "c:\\", "c:/", "d:/", "secret", "password", "api_key", "token", "venv", ".env"]
    for term in forbidden_terms:
        assert term not in response_text, f"Response leaked forbidden term: {term}"
