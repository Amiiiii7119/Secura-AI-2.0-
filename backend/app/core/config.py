"""Secura AI Backend Configuration."""
import os
from typing import List
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "Secura AI"
    APP_NAME: str = "Secura AI"
    API_VERSION: str = "1.0.0"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # 25 MiB upload limit
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024
    
    # Pixel count limit for decompression-bomb defense (approx 50 megapixels)
    MAX_IMAGE_PIXELS: int = 50_000_000
    
    # Error Level Analysis parameters
    ELA_RECOMPRESSION_QUALITY: int = 90
    ELA_JPEG_QUALITY: int = 90
    ELA_SCALE_FACTOR: float = 15.0
    
    # Database connection string (PostgreSQL)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # CORS Origins for frontend and production deployments
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://frontend-nu-olive-40.vercel.app",
        "https://frontend-n5yu6pyi5-amiiiii7119s-projects.vercel.app",
        "https://secura-ai.vercel.app",
        "*"
    ]


settings = Settings()
