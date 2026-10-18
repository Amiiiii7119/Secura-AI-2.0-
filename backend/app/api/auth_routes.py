"""
Secura AI Authentication & Session API Endpoints.
Implements Registration, Login, Logout, Session Identity, History, and Database Health Checks.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.db.session import get_db, check_db_connectivity
from app.db.models import User, SessionToken, AnalysisAudit
from app.core.auth import DatabaseAuthenticationManager

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


# --- Schemas ---

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="Unique analyst handle")
    email: str = Field(..., min_length=5, max_length=255, description="Institutional email address")
    password: str = Field(..., min_length=8, max_length=128, description="Cryptographic account password")
    role: Optional[str] = Field(default="Forensic Analyst", description="Requested role designation")


class RegisterResponse(BaseModel):
    success: bool = Field(default=True, description="Registration outcome")
    message: str = Field(..., description="Status description")
    username: str = Field(..., description="Registered analyst handle")
    email: str = Field(..., description="Registered email address")
    role: str = Field(..., description="Assigned role scope")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255, description="Analyst username or email")
    password: str = Field(..., min_length=1, max_length=128, description="Account password")


class LoginResponse(BaseModel):
    success: bool = Field(default=True, description="Authentication outcome")
    token: str = Field(..., description="Cryptographically secure 64-char hex session token")
    username: str = Field(..., description="Authenticated analyst username")
    email: Optional[str] = Field(default=None, description="Analyst email")
    role: str = Field(..., description="Role and forensic permission scope")
    expires_at: str = Field(..., description="ISO 8601 UTC session expiration timestamp")


class SessionResponse(BaseModel):
    authenticated: bool = Field(..., description="Whether a valid session is currently active")
    user_id: Optional[int] = Field(default=None, description="Internal user identifier")
    username: Optional[str] = Field(default=None, description="Active username if authenticated")
    email: Optional[str] = Field(default=None, description="Active email if authenticated")
    role: Optional[str] = Field(default=None, description="Active role if authenticated")
    expires_at: Optional[str] = Field(default=None, description="Expiration timestamp if authenticated")


class LogoutResponse(BaseModel):
    success: bool = Field(default=True, description="Whether logout succeeded")
    message: str = Field(default="Session successfully terminated", description="Safe status message")


class AnalysisHistoryItem(BaseModel):
    id: int
    media_type: str
    filename: str
    predicted_label: str
    confidence_pct: float
    evidence_summary: Optional[str] = None
    created_at: str


class DbStatusResponse(BaseModel):
    connected: bool
    database_type: str
    latency_ms: float
    error: Optional[str] = None


# --- Token Extraction & Dependencies ---

def extract_token(
    authorization: Optional[str] = Header(None),
    secura_session: Optional[str] = Cookie(None)
) -> Optional[str]:
    """Extract session token from either Authorization Bearer header or HttpOnly cookie."""
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1].strip()
    return secura_session


def get_current_user_optional(
    token: Optional[str] = Depends(extract_token),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Return User if token is valid, else None without raising exception."""
    if not token:
        return None
    res = DatabaseAuthenticationManager.validate_session_token(db, token)
    if res:
        return res[0]
    return None


def get_current_user(
    token: Optional[str] = Depends(extract_token),
    db: Session = Depends(get_db)
) -> User:
    """Enforce authentication on protected routes. Raises HTTP 401 if invalid or missing."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing session credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    res = DatabaseAuthenticationManager.validate_session_token(db, token)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or credentials have been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return res[0]


# --- Route Handlers ---

@auth_router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    req: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new analyst account with persistent database record."""
    user, err = DatabaseAuthenticationManager.register_user(
        db,
        username=req.username,
        email=req.email,
        password=req.password,
        role=req.role or "Forensic Analyst"
    )
    if err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err
        )
    return RegisterResponse(
        success=True,
        message="Account registered successfully. You may now sign in.",
        username=user.username,
        email=user.email,
        role=user.role
    )


@auth_router.post("/login", response_model=LoginResponse)
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Authenticate analyst credentials against PostgreSQL database."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "")

    user, err = DatabaseAuthenticationManager.authenticate_credentials(
        db,
        identifier=req.username,
        password=req.password,
        client_ip=client_ip
    )

    if not user:
        status_code = status.HTTP_429_TOO_MANY_REQUESTS if "wait" in (err or "").lower() else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(
            status_code=status_code,
            detail=err or "Invalid username or password"
        )

    # Issue persistent session
    session_record = DatabaseAuthenticationManager.create_session(
        db,
        user=user,
        client_ip=client_ip,
        user_agent=user_agent
    )

    # Set secure HttpOnly cookie
    response.set_cookie(
        key="secura_session",
        value=session_record.token,
        max_age=86400,
        httponly=True,
        samesite="lax",
        secure=False  # Set to True on production HTTPS via environment
    )

    return LoginResponse(
        success=True,
        token=session_record.token,
        username=user.username,
        email=user.email,
        role=user.role,
        expires_at=session_record.expires_at.isoformat()
    )


@auth_router.post("/logout", response_model=LogoutResponse)
def logout(
    response: Response,
    token: Optional[str] = Depends(extract_token),
    db: Session = Depends(get_db)
):
    """Revoke active session token in PostgreSQL and clear cookie."""
    if token:
        DatabaseAuthenticationManager.revoke_session(db, token)

    response.delete_cookie(key="secura_session")
    return LogoutResponse(
        success=True,
        message="Session terminated successfully"
    )


@auth_router.get("/session", response_model=SessionResponse)
@auth_router.get("/me", response_model=SessionResponse)
def get_current_session(
    token: Optional[str] = Depends(extract_token),
    db: Session = Depends(get_db)
):
    """Inspect and return current active session information."""
    if not token:
        return SessionResponse(authenticated=False)

    res = DatabaseAuthenticationManager.validate_session_token(db, token)
    if not res:
        return SessionResponse(authenticated=False)

    user, session = res
    return SessionResponse(
        authenticated=True,
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        expires_at=session.expires_at.isoformat()
    )


@auth_router.get("/history", response_model=List[AnalysisHistoryItem])
def get_user_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve user-owned forensic examination history from database."""
    records = db.query(AnalysisAudit).filter(
        AnalysisAudit.user_id == current_user.id
    ).order_by(AnalysisAudit.created_at.desc()).limit(50).all()

    return [
        AnalysisHistoryItem(
            id=r.id,
            media_type=r.media_type,
            filename=r.filename,
            predicted_label=r.predicted_label,
            confidence_pct=r.confidence_pct,
            evidence_summary=r.evidence_summary,
            created_at=r.created_at.isoformat() if r.created_at else ""
        )
        for r in records
    ]


@auth_router.get("/db-status", response_model=DbStatusResponse)
def get_database_status():
    """Verify live database connectivity and measure latency."""
    res = check_db_connectivity()
    return DbStatusResponse(
        connected=res["connected"],
        database_type=res["database_type"],
        latency_ms=res["latency_ms"],
        error=res["error"]
    )
