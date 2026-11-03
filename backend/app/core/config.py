"""
config.py

Centralized configuration settings for the DocQuery backend using Pydantic Settings.
Environment variables can override any setting here or via a .env file.
"""

from pathlib import Path
from typing import List, Set
from pydantic_settings import BaseSettings, SettingsConfigDict


# Path resolution:
# __file__ is in backend/app/core/config.py
# parents[0] = core
# parents[1] = app
# parents[2] = backend
# parents[3] = project root (DocQuery)
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parents[2]
PROJECT_ROOT = CURRENT_FILE.parents[3]

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DATABASE_PATH = DATA_DIR / "docquery.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH}"


class Settings(BaseSettings):
    """Application settings and configuration."""

    PROJECT_NAME: str = "DocQuery API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = ""
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security & JWT
    SECRET_KEY: str = "docquery-super-secret-key-change-in-production-2026!#"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = DEFAULT_DATABASE_URL

    # Storage paths
    STORAGE_DIR: Path = BACKEND_DIR / "storage"
    DOCUMENTS_DIR: Path = BACKEND_DIR / "storage" / "documents"
    AVATARS_DIR: Path = BACKEND_DIR / "storage" / "profile_pictures"

    # File Upload Limits & Formats
    MAX_FILE_SIZE_MB: int = 25
    MAX_AVATAR_SIZE_MB: int = 5
    ALLOWED_DOCUMENT_EXTENSIONS: Set[str] = {".pdf", ".txt", ".md"}
    ALLOWED_AVATAR_EXTENSIONS: Set[str] = {".png", ".jpg", ".jpeg", ".webp"}

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*"
    ]

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def max_avatar_size_bytes(self) -> int:
        return self.MAX_AVATAR_SIZE_MB * 1024 * 1024


settings = Settings()

# Ensure critical storage directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
settings.AVATARS_DIR.mkdir(parents=True, exist_ok=True)
