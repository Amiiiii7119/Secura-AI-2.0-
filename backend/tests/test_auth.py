import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import (
    AuthenticationManager,
    get_auth_manager,
    hash_password,
    verify_password,
    DEFAULT_ADMIN_USER,
    DEFAULT_ADMIN_PASSWORD,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_auth_state():
    """Reset failed attempts and test sessions before each test."""
    from app.db.session import init_db
    init_db()
    mgr = get_auth_manager()
    mgr._failed_attempts.clear()
    mgr._sessions.clear()
    yield
    mgr._failed_attempts.clear()
    mgr._sessions.clear()


def test_password_hashing_and_verification():
    raw = "TopSecretForensicKey2026!"
    h1, s1 = hash_password(raw)
    h2, s2 = hash_password(raw)

    # Different salts must yield different hashes
    assert s1 != s2
    assert h1 != h2

    # Verification must succeed
    assert verify_password(raw, h1, s1) is True
    assert verify_password(raw, h2, s2) is True
    # Bad password must fail
    assert verify_password("WrongPassword!", h1, s1) is False


def test_login_success(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": DEFAULT_ADMIN_USER, "password": DEFAULT_ADMIN_PASSWORD}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["username"] == DEFAULT_ADMIN_USER
    assert len(data["token"]) == 64
    assert "secura_session" in res.cookies


def test_login_failure_invalid_credentials(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": DEFAULT_ADMIN_USER, "password": "WrongPassword123!"}
    )
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


def test_rate_limiting_after_repeated_failures(client):
    # Attempt 5 consecutive invalid logins
    for _ in range(5):
        res = client.post(
            "/api/v1/auth/login",
            json={"username": DEFAULT_ADMIN_USER, "password": "WrongPassword!"}
        )
        assert res.status_code == 401

    # 6th attempt must be blocked by rate limiter
    blocked_res = client.post(
        "/api/v1/auth/login",
        json={"username": DEFAULT_ADMIN_USER, "password": "WrongPassword!"}
    )
    assert blocked_res.status_code == 429
    assert "Too many failed login attempts" in blocked_res.json()["detail"]


def test_session_validation_endpoint(client):
    # 1. Check unauthenticated session
    res_unauth = client.get("/api/v1/auth/session")
    assert res_unauth.status_code == 200
    assert res_unauth.json()["authenticated"] is False

    # 2. Login to acquire session
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": DEFAULT_ADMIN_USER, "password": DEFAULT_ADMIN_PASSWORD}
    )
    token = login_res.json()["token"]

    # 3. Verify via Bearer header
    res_auth_header = client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_auth_header.status_code == 200
    assert res_auth_header.json()["authenticated"] is True
    assert res_auth_header.json()["username"] == DEFAULT_ADMIN_USER

    # 4. Verify via Cookie
    res_auth_cookie = client.get(
        "/api/v1/auth/session",
        cookies={"secura_session": token}
    )
    assert res_auth_cookie.status_code == 200
    assert res_auth_cookie.json()["authenticated"] is True


def test_logout_revokes_session(client):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": DEFAULT_ADMIN_USER, "password": DEFAULT_ADMIN_PASSWORD}
    )
    token = login_res.json()["token"]

    # Logout
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # Validate session is now revoked
    session_res = client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert session_res.status_code == 200
    assert session_res.json()["authenticated"] is False
