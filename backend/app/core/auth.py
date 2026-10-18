"""
Secura AI Authentication & Session Lifecycle Management.
Provides NIST-compliant password hashing, database-persisted accounts/sessions,
and rate-limiting defenses against brute-force attacks.
"""
import hashlib
import hmac
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.models import User, SessionToken, AnalysisAudit

logger = logging.getLogger(__name__)

# Security Parameters
PBKDF2_ITERATIONS = 100_000
HASH_ALGORITHM = "sha256"
SESSION_LIFETIME_SECONDS = 86400  # 24 hours
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 60

# Default bootstrap credentials for single-workstation forensic operations
DEFAULT_ADMIN_USER = os.getenv("SECURA_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_EMAIL = os.getenv("SECURA_ADMIN_EMAIL", "admin@secura.ai")
DEFAULT_ADMIN_PASSWORD = os.getenv("SECURA_ADMIN_PASSWORD", "SecuraForensics2026!")
ADMIN_ROLE = "Lead Forensic Examiner"


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a 16-byte cryptographically secure salt."""
    if salt is None:
        salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS
    )
    return key.hex(), salt.hex()


def verify_password(password: str, stored_hash_hex: str, stored_salt_hex: str) -> bool:
    """Verify password against stored hash using constant-time comparison."""
    try:
        salt = bytes.fromhex(stored_salt_hex)
        computed_key = hashlib.pbkdf2_hmac(
            HASH_ALGORITHM,
            password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS
        )
        stored_key = bytes.fromhex(stored_hash_hex)
        return hmac.compare_digest(computed_key, stored_key)
    except Exception as exc:
        logger.error(f"Error during password verification: {exc}")
        return False


class RateLimiter:
    """Thread-safe sliding-window rate limiter for authentication endpoints."""
    def __init__(self, max_attempts: int = MAX_FAILED_ATTEMPTS, window_seconds: int = LOCKOUT_WINDOW_SECONDS):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def record_attempt(self, key: str) -> None:
        """Record an attempt timestamp for an identifier or IP."""
        now = time.time()
        with self._lock:
            attempts = self._attempts.get(key, [])
            attempts = [t for t in attempts if now - t < self.window_seconds]
            attempts.append(now)
            self._attempts[key] = attempts

    def is_locked(self, key: str) -> Tuple[bool, int]:
        """Check if identifier or IP is rate-limited. Returns (is_locked, remaining_lockout_seconds)."""
        now = time.time()
        with self._lock:
            attempts = self._attempts.get(key, [])
            attempts = [t for t in attempts if now - t < self.window_seconds]
            self._attempts[key] = attempts
            if len(attempts) >= self.max_attempts:
                oldest = attempts[0]
                remaining = max(1, int(self.window_seconds - (now - oldest)))
                return True, remaining
            return False, 0

    def clear(self, key: str) -> None:
        """Clear attempt history on successful authentication."""
        with self._lock:
            self._attempts.pop(key, None)


# Global rate limiter instance
auth_rate_limiter = RateLimiter()


class DatabaseAuthenticationManager:
    """Database-backed Authentication and Session Lifecycle Manager."""

    @staticmethod
    def ensure_bootstrap_admin(db: Session) -> User:
        """Ensure default admin account exists in database."""
        admin = db.query(User).filter(
            or_(User.username == DEFAULT_ADMIN_USER, User.email == DEFAULT_ADMIN_EMAIL)
        ).first()
        if not admin:
            hashed, salt = hash_password(DEFAULT_ADMIN_PASSWORD)
            admin = User(
                username=DEFAULT_ADMIN_USER,
                email=DEFAULT_ADMIN_EMAIL,
                hashed_password=hashed,
                salt=salt,
                role=ADMIN_ROLE,
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            logger.info("Bootstrap admin account initialized in database.")
        return admin

    @staticmethod
    def register_user(
        db: Session,
        username: str,
        email: str,
        password: str,
        role: str = "Forensic Analyst"
    ) -> Tuple[Optional[User], Optional[str]]:
        """Register a new analyst account in PostgreSQL. Returns (user, error_message)."""
        # 1. Validation
        username = username.strip()
        email = email.strip().lower()
        if len(username) < 3 or len(username) > 64:
            return None, "Username must be between 3 and 64 characters."
        if "@" not in email or "." not in email:
            return None, "Invalid email address format."
        if len(password) < 8:
            return None, "Password must be at least 8 characters long."

        # 2. Check collision
        existing = db.query(User).filter(or_(User.username == username, User.email == email)).first()
        if existing:
            if existing.username == username:
                return None, "Username already registered."
            return None, "Email address already registered."

        # 3. Hash & Persist
        hashed, salt = hash_password(password)
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed,
            salt=salt,
            role=role,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user, None

    @staticmethod
    def authenticate_credentials(
        db: Session,
        identifier: str,
        password: str,
        client_ip: str = "127.0.0.1"
    ) -> Tuple[Optional[User], Optional[str]]:
        """Authenticate user against PostgreSQL with rate-limiting. Returns (user, error_message)."""
        # Ensure bootstrap admin exists
        DatabaseAuthenticationManager.ensure_bootstrap_admin(db)

        # Check rate limiter
        rate_key = f"{client_ip}:{identifier.lower()}"
        locked, remaining = auth_rate_limiter.is_locked(rate_key)
        if locked:
            return None, f"Too many failed login attempts. Please wait {remaining} seconds before retrying."

        user = db.query(User).filter(
            or_(User.username == identifier, User.email == identifier.lower())
        ).first()

        if not user or not user.is_active:
            auth_rate_limiter.record_attempt(rate_key)
            return None, "Invalid username or password."

        if not verify_password(password, user.hashed_password, user.salt):
            auth_rate_limiter.record_attempt(rate_key)
            return None, "Invalid username or password."

        # Success - clear lockout
        auth_rate_limiter.clear(rate_key)
        return user, None

    @staticmethod
    def create_session(
        db: Session,
        user: User,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> SessionToken:
        """Generate cryptographically secure 64-char hex session token in PostgreSQL."""
        token_str = secrets.token_hex(32)
        expires = datetime.now(timezone.utc) + timedelta(seconds=SESSION_LIFETIME_SECONDS)

        session_record = SessionToken(
            user_id=user.id,
            token=token_str,
            role=user.role,
            ip_address=client_ip[:45] if client_ip else None,
            user_agent=user_agent[:255] if user_agent else None,
            expires_at=expires,
            is_revoked=False
        )
        db.add(session_record)
        db.commit()
        db.refresh(session_record)
        return session_record

    @staticmethod
    def validate_session_token(db: Session, token: str) -> Optional[Tuple[User, SessionToken]]:
        """Validate session token against database records. Returns (user, session) or None."""
        if not token or len(token) != 64:
            return None

        record = db.query(SessionToken).filter(
            SessionToken.token == token,
            SessionToken.is_revoked == False
        ).first()

        if not record or not record.is_valid():
            return None

        user = db.query(User).filter(User.id == record.user_id, User.is_active == True).first()
        if not user:
            return None

        return user, record

    @staticmethod
    def revoke_session(db: Session, token: str) -> bool:
        """Revoke active session token in database."""
        record = db.query(SessionToken).filter(SessionToken.token == token).first()
        if record:
            record.is_revoked = True
            db.commit()
            return True
        return False

    @staticmethod
    def record_analysis(
        db: Session,
        user_id: Optional[int],
        media_type: str,
        filename: str,
        predicted_label: str,
        confidence_pct: float,
        evidence_summary: Optional[str] = None
    ) -> AnalysisAudit:
        """Persist forensic media examination audit log to PostgreSQL."""
        audit = AnalysisAudit(
            user_id=user_id,
            media_type=media_type,
            filename=filename,
            predicted_label=predicted_label,
            confidence_pct=confidence_pct,
            evidence_summary=evidence_summary
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit


# Backwards compatibility singleton for legacy imports
class _LegacyAuthManagerAdapter:
    def __init__(self):
        self._test_sessions = {}

    @property
    def _failed_attempts(self):
        return auth_rate_limiter._attempts

    @property
    def _sessions(self):
        return self._test_sessions

    def authenticate(self, username: str, password: str, client_ip: str = "127.0.0.1"):
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            user, err = DatabaseAuthenticationManager.authenticate_credentials(db, username, password, client_ip)
            if user:
                session = DatabaseAuthenticationManager.create_session(db, user, client_ip)
                return True, session.token, user.role, session.expires_at.isoformat()
            return False, "", "", err or "Authentication failed"

    def validate_session(self, token: str):
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            res = DatabaseAuthenticationManager.validate_session_token(db, token)
            if res:
                user, session = res
                return True, user.username, user.role, session.expires_at.isoformat()
            return False, None, None, None

    def terminate_session(self, token: str):
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            return DatabaseAuthenticationManager.revoke_session(db, token)


def get_auth_manager():
    return _LegacyAuthManagerAdapter()

AuthenticationManager = _LegacyAuthManagerAdapter
