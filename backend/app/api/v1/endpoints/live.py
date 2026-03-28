"""
StreetSense -- Live Detection API Endpoint

Supports dashcam/webcam live detection:
  POST /live/frame    Process a single video frame (used by frontend webcam capture)

The frontend captures frames from webcam/dashcam via getUserMedia,
sends them to this endpoint, and displays results in real-time.
"""

import time
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from loguru import logger

from app.services import ai_service
from app.services.auth_service import get_current_user
from app.models.user import User
from app.utils.file_utils import read_image_from_upload, validate_image_file

router = APIRouter(prefix="/live", tags=["live-detection"])


@router.post("/frame")
async def process_frame(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Process a single video frame for real-time detection.
    Returns detections without saving to database (for speed).
    Use /complaints/upload to save detections as complaints.
    """
    content = await file.read()
    try:
        image = read_image_from_upload(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await ai_service.run_inference(image)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Live frame inference failed: {e}")
        raise HTTPException(status_code=500, detail="Detection failed")

    return {
        "detections": result["detections"],
        "processing_time_ms": result["processing_time_ms"],
        "frame_shape": result["image_shape"],
        "annotated_image_url": result.get("annotated_image_url"),
    }
