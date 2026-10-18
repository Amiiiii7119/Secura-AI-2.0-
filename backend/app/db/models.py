"""
Secura AI Persistent ORM Database Models.
Implements User Accounts, Session Tokens, and Analysis Audit records.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class User(Base):
    """Secura AI Analyst / Officer User Account."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(String(64), default="Forensic Analyst", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    sessions = relationship("SessionToken", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("AnalysisAudit", back_populates="user")

    def __repr__(self):
        return f"<User id={self.id} username={self.username} role={self.role}>"


class SessionToken(Base):
    """Cryptographic Session Token for Stateful & Stateless User Authentication."""
    __tablename__ = "session_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(64), unique=True, index=True, nullable=False)
    role = Column(String(64), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    user = relationship("User", back_populates="sessions")

    def is_valid(self) -> bool:
        """Verify token is not revoked and not expired."""
        if self.is_revoked:
            return False
        # Normalize comparison timezone
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp > now


class AnalysisAudit(Base):
    """Persistent Forensic Media Examination Log."""
    __tablename__ = "analysis_audits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    media_type = Column(String(32), nullable=False)  # 'image' or 'video'
    filename = Column(String(255), nullable=False)
    predicted_label = Column(String(64), nullable=False)
    confidence_pct = Column(Float, nullable=False)
    evidence_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    user = relationship("User", back_populates="analyses")

    def __repr__(self):
        return f"<AnalysisAudit id={self.id} media_type={self.media_type} label={self.predicted_label}>"
