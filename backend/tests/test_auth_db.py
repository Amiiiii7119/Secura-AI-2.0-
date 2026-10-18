"""
Unit and Integration Tests for Secura AI Database & Authentication System.
Tests registration, login, token management, password hashing, and user data isolation.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.db.models import User, SessionToken, AnalysisAudit
from app.core.auth import (
    hash_password,
    verify_password,
    DatabaseAuthenticationManager,
    RateLimiter
)

# Shared in-memory SQLite with StaticPool so all connections share the same memory instance
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    return TestClient(app)


def test_password_hashing():
    """Verify PBKDF2-HMAC-SHA256 password hashing and constant-time verification."""
    password = "SecuraSecretPassword2026!"
    hashed, salt = hash_password(password)
    assert len(hashed) == 64
    assert len(salt) == 32
    assert verify_password(password, hashed, salt) is True
    assert verify_password("WrongPassword123", hashed, salt) is False


def test_user_registration(client):
    """Verify successful user registration via API."""
    payload = {
        "username": "investigator_alice",
        "email": "alice@secura.ai",
        "password": "StrongPassword2026!",
        "role": "Forensic Specialist"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    assert data["username"] == "investigator_alice"
    assert data["email"] == "alice@secura.ai"
    assert data["role"] == "Forensic Specialist"


def test_user_registration_duplicate_username(client):
    """Verify duplicate usernames are rejected."""
    payload = {
        "username": "investigator_bob",
        "email": "bob1@secura.ai",
        "password": "StrongPassword2026!"
    }
    resp1 = client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    payload2 = {
        "username": "investigator_bob",
        "email": "bob2@secura.ai",
        "password": "StrongPassword2026!"
    }
    resp2 = client.post("/api/v1/auth/register", json=payload2)
    assert resp2.status_code == 400
    assert "Username already registered" in resp2.json()["detail"]


def test_user_registration_short_password(client):
    """Verify password length requirement enforcement."""
    payload = {
        "username": "investigator_charlie",
        "email": "charlie@secura.ai",
        "password": "short"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422 or resp.status_code == 400


def test_login_and_token_generation(client):
    """Verify login generates secure 64-char hex token and sets cookie."""
    # 1. Register
    reg_payload = {
        "username": "dan_analyst",
        "email": "dan@secura.ai",
        "password": "DanPassword2026!",
        "role": "Senior Examiner"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # 2. Login
    login_payload = {
        "username": "dan_analyst",
        "password": "DanPassword2026!"
    }
    login_resp = client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["success"] is True
    assert len(data["token"]) == 64
    assert data["username"] == "dan_analyst"
    assert data["role"] == "Senior Examiner"
    assert "secura_session" in login_resp.cookies

    # 3. Verify session via /me
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["authenticated"] is True
    assert me_data["username"] == "dan_analyst"


def test_login_incorrect_password(client):
    """Verify incorrect password returns 401."""
    reg_payload = {
        "username": "eva_agent",
        "email": "eva@secura.ai",
        "password": "EvaPassword2026!"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    resp = client.post("/api/v1/auth/login", json={"username": "eva_agent", "password": "WrongPassword!"})
    assert resp.status_code == 401
    assert "Invalid username" in resp.json()["detail"]


def test_logout_revocation(client):
    """Verify logout revokes active session."""
    reg_payload = {
        "username": "frank_examiner",
        "email": "frank@secura.ai",
        "password": "FrankPassword2026!"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_resp = client.post("/api/v1/auth/login", json={"username": "frank_examiner", "password": "FrankPassword2026!"})
    token = login_resp.json()["token"]

    # Logout
    logout_resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    # Session should now be invalid
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["authenticated"] is False


def test_database_status_endpoint(client):
    """Verify database status and connectivity health endpoint."""
    resp = client.get("/api/v1/auth/db-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "connected" in data
    assert "database_type" in data
    assert "latency_ms" in data


def test_rate_limiter():
    """Verify rate limiter blocks after threshold attempts."""
    limiter = RateLimiter(max_attempts=3, window_seconds=10)
    key = "test_ip"
    assert limiter.is_locked(key)[0] is False
    limiter.record_attempt(key)
    limiter.record_attempt(key)
    assert limiter.is_locked(key)[0] is False
    limiter.record_attempt(key)
    locked, remaining = limiter.is_locked(key)
    assert locked is True
    assert remaining > 0
    limiter.clear(key)
    assert limiter.is_locked(key)[0] is False
