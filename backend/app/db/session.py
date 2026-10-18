"""
Secura AI Database Engine and Session Management.
Supports genuine managed PostgreSQL (Neon, Supabase, RDS) with connection pooling.
"""
import logging
import os
import time
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logger = logging.getLogger(__name__)

# Base declarative class for all ORM models
Base = declarative_base()

# Retrieve database connection string from environment
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SECURA_DATABASE_URL")

def get_engine_url(raw_url: str | None) -> str:
    """Normalize PostgreSQL URL for SQLAlchemy compatibility."""
    if not raw_url:
        # Fallback to local SQLite file for development/testing when no external DB is configured
        local_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "secura_local.db"))
        return f"sqlite:///{local_db_path}"
    
    # Handle cloud providers (Neon, Supabase, Vercel) that give postgres:// instead of postgresql://
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
        raw_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        
    return raw_url

# Configure engine with robust production pooling parameters
SQLALCHEMY_DATABASE_URL = get_engine_url(DATABASE_URL)
is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,      # Tests connection liveness before checkout (essential for serverless/cloud DBs)
        pool_recycle=300,        # Recycle idle connections every 5 minutes
        pool_size=10,            # Standard connection pool size
        max_overflow=20,         # Allow burst connections during concurrent forensic batches
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database session with automatic transaction handling."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def check_db_connectivity() -> dict:
    """Verify database connectivity and measure latency."""
    start_time = time.time()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            latency_ms = round((time.time() - start_time) * 1000, 2)
            db_type = "PostgreSQL" if not is_sqlite else "SQLite (Fallback/Local)"
            return {
                "connected": result == 1,
                "database_type": db_type,
                "latency_ms": latency_ms,
                "error": None
            }
    except Exception as exc:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"Database connectivity check failed: {exc}")
        return {
            "connected": False,
            "database_type": "Unknown",
            "latency_ms": latency_ms,
            "error": str(exc)
        }

def init_db():
    """Create all tables defined in models if they do not exist."""
    from app.db import models  # noqa
    Base.metadata.create_all(bind=engine)
