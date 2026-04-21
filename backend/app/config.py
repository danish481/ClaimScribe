"""
ClaimScribe AI - Configuration Module
Centralized configuration with environment variable support
"""

import os
import secrets
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field

# ── Base Paths ────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"

# Ensure directories exist
for d in [DATA_DIR, UPLOAD_DIR, EXPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── App ───────────────────────────────────────────────
    APP_NAME: str = "ClaimScribe AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = "INFO"

    # ── Security ──────────────────────────────────────────
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ENCRYPTION_KEY: str = ""  # Fernet key for document encryption
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── API ───────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:5174,http://localhost:5173,http://localhost:8001"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/claimscribe.db"

    # ── Hosting ───────────────────────────────────────────
    ALLOWED_HOSTS: str = "*"  # Comma-separated; "*" = all in dev
    RENDER_EXTERNAL_URL: str = ""  # Auto-populated by Render at runtime

    # ── MLflow ────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = f"file://{DATA_DIR}/mlruns"
    MLFLOW_EXPERIMENT_NAME: str = "claimscribe-document-classification"
    MLFLOW_ARTIFACT_ROOT: str = str(DATA_DIR / "mlruns")

    # ── LLM (Gemini) ──────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.3
    GEMINI_MAX_TOKENS: int = 2048

    # ── OCR ───────────────────────────────────────────────
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    OCR_DPI: int = 300

    # ── Processing ────────────────────────────────────────
    CLASSIFICATION_CONFIDENCE_THRESHOLD: float = 0.6
    MAX_DOCUMENTS_PER_BATCH: int = 100

    # ── Export ────────────────────────────────────────────
    EXPORT_LINK_TTL_HOURS: int = 24

    # ── Pipeline ──────────────────────────────────────────
    PIPELINE_ENABLED: bool = True
    PIPELINE_SCHEDULE_MINUTES: int = 30   # how often the scheduler fires
    PIPELINE_STORAGE_BACKEND: str = "local"  # local | s3 | gcs
    PIPELINE_S3_BUCKET: str = ""
    PIPELINE_GCS_BUCKET: str = ""

    # ── HIPAA / Compliance ────────────────────────────────
    AUDIT_LOG_RETENTION_DAYS: int = 2555  # 7 years
    AUTO_PURGE_ENABLED: bool = True
    AUTO_PURGE_DAYS: int = 90

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# ── Convenience Exports ───────────────────────────────────
settings = get_settings()
