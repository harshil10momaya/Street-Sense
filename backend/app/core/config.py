"""
StreetSense — Application Configuration

Loads settings from environment variables with sensible defaults.
Uses pydantic-settings for validation and type coercion.
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve project root (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Central configuration loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "StreetSense"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = True

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://streetsense:streetsense_pass@localhost:5432/streetsense_db"
    )
    database_sync_url: str = (
        "postgresql://streetsense:streetsense_pass@localhost:5432/streetsense_db"
    )

    # --- AI Models ---
    yolo_weights_path: str = "ai/weights/best.pt"
    midas_model_type: str = "DPT_Large"
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45

    # --- Severity ---
    severity_low_max: float = 0.33
    severity_medium_max: float = 0.66

    # --- Uploads ---
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20

    # --- Geo ---
    default_latitude: float = 13.0827
    default_longitude: float = 80.2707
    geocoder_user_agent: str = "streetsense-app"

    # --- Notifications ---
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@streetsense.app"

    # --- CORS ---
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # --- Security ---
    secret_key: str = "change-this-to-a-random-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    @property
    def upload_path(self) -> Path:
        """Resolved upload directory path."""
        path = BASE_DIR / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def weights_path(self) -> Path:
        """Resolved YOLO weights path."""
        return BASE_DIR / self.yolo_weights_path

    @property
    def max_upload_bytes(self) -> int:
        """Max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024


# Singleton instance — import this everywhere
settings = Settings()
