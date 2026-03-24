"""
StreetSense — Logging Configuration

Configures structured logging with loguru.
"""

import sys
from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging."""
    # Remove default handler
    logger.remove()

    # Console handler
    log_level = "DEBUG" if settings.debug else "INFO"
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        colorize=True,
    )

    # File handler (rotated daily, kept 7 days)
    logger.add(
        "logs/streetsense_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="INFO",
        rotation="00:00",
        retention="7 days",
        compression="zip",
        enqueue=True,  # Thread-safe
    )

    logger.info(f"Logging initialized — level={log_level}, env={settings.environment}")
