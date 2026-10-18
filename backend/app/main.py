"""Secura AI Main Application Entrypoint."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.session import init_db
from app.api.routes import router
from app.api.auth_routes import auth_router
from app.api.social_routes import social_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle handler."""
    logger.info("Initializing Secura AI database schema...")
    try:
        init_db()
        logger.info("Secura AI database schema verified.")
    except Exception as exc:
        logger.warning(f"Database initialization warning (will retry on connection): {exc}")
    yield


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        description="Secura AI - Forensic Media Intelligence Platform",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # CORS configuration supporting deployed frontend origins and local dev
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(social_router, prefix="/api/v1")
    application.include_router(router)

    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global exception caught on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during processing. Stack traces are omitted for security."
            }
        )

    return application


app = create_application()
