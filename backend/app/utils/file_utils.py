"""
StreetSense -- File Upload Utilities

Handles image file saving, validation, and path management.
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import UploadFile
from loguru import logger

from app.core.config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


def validate_image_file(file: UploadFile) -> Optional[str]:
    """Validate an uploaded image file. Returns error message or None."""
    if not file.filename:
        return "No filename provided"

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"Invalid file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}"

    if file.size and file.size > settings.max_upload_bytes:
        max_mb = settings.max_upload_size_mb
        return f"File too large ({file.size / 1e6:.1f} MB). Max: {max_mb} MB"

    return None


def generate_filename(original_name: str, prefix: str = "") -> str:
    """Generate a unique filename preserving the original extension."""
    ext = Path(original_name).suffix.lower()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}{ext}"
    return f"{timestamp}_{unique_id}{ext}"


async def save_upload(
    file: UploadFile,
    subdirectory: str = "uploads",
    prefix: str = "",
) -> Path:
    """
    Save an uploaded file to disk.

    Args:
        file: FastAPI UploadFile
        subdirectory: Subdirectory inside the upload path
        prefix: Optional filename prefix

    Returns:
        Path to saved file
    """
    dest_dir = settings.upload_path / subdirectory
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = generate_filename(file.filename, prefix)
    dest_path = dest_dir / filename

    content = await file.read()
    dest_path.write_bytes(content)

    logger.debug(f"Saved upload: {dest_path} ({len(content)} bytes)")
    return dest_path


def save_image(
    image: np.ndarray,
    subdirectory: str,
    name: str,
) -> Path:
    """
    Save an OpenCV image (numpy array) to disk.

    Args:
        image: BGR image array
        subdirectory: Subdirectory inside upload path
        name: Filename (with extension)

    Returns:
        Path to saved file
    """
    dest_dir = settings.upload_path / subdirectory
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / name
    cv2.imwrite(str(dest_path), image)
    logger.debug(f"Saved image: {dest_path}")
    return dest_path


def get_relative_url(absolute_path: Path) -> str:
    """Convert an absolute file path to a URL-friendly relative path."""
    try:
        rel = absolute_path.relative_to(settings.upload_path)
        return f"/uploads/{rel.as_posix()}"
    except ValueError:
        return str(absolute_path)


def read_image_from_upload(content: bytes) -> np.ndarray:
    """Convert uploaded file bytes to an OpenCV BGR image."""
    nparr = np.frombuffer(content, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image from uploaded bytes")
    return image
