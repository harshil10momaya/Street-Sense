"""
StreetSense -- Live Detection API Endpoint

Supports:
  POST /live/frame           Detect only (no save, fast preview)
  POST /live/frame-report    Detect + geo-tag + auto-create complaints
  POST /live/capture         Single photo capture + detect + save complaint
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.services import ai_service, complaint_service, geo_service
from app.services.auth_service import get_current_user
from app.services.notification_service import notify
from app.models.user import User
from app.utils.file_utils import read_image_from_upload, save_upload, get_relative_url

router = APIRouter(prefix="/live", tags=["live-detection"])


@router.post("/frame")
async def process_frame(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Process a single video frame -- detection only, no database save.
    Used for real-time preview overlay on the video feed.
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


@router.post("/frame-report")
async def frame_report(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a video frame WITH geo-tagging and auto-complaint creation.
    Called continuously during live detection when GPS is available.

    For each detection found:
      1. Run AI inference
      2. Reverse geocode the GPS coordinates
      3. Create a complaint in the database
      4. Trigger notifications

    Returns detections + complaint IDs for tracking.
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
        logger.error(f"Live frame-report inference failed: {e}")
        raise HTTPException(status_code=500, detail="Detection failed")

    # If no detections, return quickly
    if not result["detections"]:
        return {
            "detections": [],
            "complaints_created": 0,
            "processing_time_ms": result["processing_time_ms"],
        }

    # Save the frame image
    saved_path = await _save_frame_bytes(content, "live_frames")
    image_url = get_relative_url(saved_path) if saved_path else None

    # Create complaints for each detection
    complaint_ids = []
    for det in result["detections"]:
        try:
            location_info = geo_service.process_location(
                latitude=latitude,
                longitude=longitude,
                issue_type=det["issue_type"],
                severity=det["severity"],
            )

            bbox = det["bbox"]
            complaint = await complaint_service.create_complaint(
                db=db,
                issue_type=det["issue_type"],
                confidence=det["confidence"],
                severity=det["severity"],
                severity_score=det["severity_score"],
                depth_value=det.get("depth_value"),
                bbox_x=bbox["x"],
                bbox_y=bbox["y"],
                bbox_w=bbox["w"],
                bbox_h=bbox["h"],
                latitude=latitude,
                longitude=longitude,
                address=location_info.get("address"),
                ward=location_info.get("ward"),
                zone=location_info.get("zone"),
                image_path=image_url,
                annotated_image_path=result.get("annotated_image_url"),
                depth_map_path=result.get("depth_map_url"),
                source="live_feed",
                department=location_info.get("department"),
                created_by=str(current_user.id),
            )
            complaint_ids.append(str(complaint.id))

            try:
                await notify.on_complaint_created(complaint, location_info)
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Live complaint creation failed: {e}")

    await db.commit()

    return {
        "detections": result["detections"],
        "complaints_created": len(complaint_ids),
        "complaint_ids": complaint_ids,
        "latitude": latitude,
        "longitude": longitude,
        "processing_time_ms": result["processing_time_ms"],
        "annotated_image_url": result.get("annotated_image_url"),
    }


@router.post("/capture")
async def capture_photo(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Single photo capture from live feed -- saves image + creates complaints.
    Used when user manually taps the capture button during live detection.
    Higher quality than continuous frame-report.
    """
    content = await file.read()
    try:
        image = read_image_from_upload(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save original at higher quality
    saved_path = await _save_frame_bytes(content, "captures")
    image_url = get_relative_url(saved_path) if saved_path else None

    try:
        result = await ai_service.run_inference(image)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Capture inference failed: {e}")
        raise HTTPException(status_code=500, detail="Detection failed")

    complaint_ids = []
    for det in result["detections"]:
        try:
            location_info = geo_service.process_location(
                latitude=latitude,
                longitude=longitude,
                issue_type=det["issue_type"],
                severity=det["severity"],
            )

            bbox = det["bbox"]
            complaint = await complaint_service.create_complaint(
                db=db,
                issue_type=det["issue_type"],
                confidence=det["confidence"],
                severity=det["severity"],
                severity_score=det["severity_score"],
                depth_value=det.get("depth_value"),
                bbox_x=bbox["x"],
                bbox_y=bbox["y"],
                bbox_w=bbox["w"],
                bbox_h=bbox["h"],
                latitude=latitude,
                longitude=longitude,
                address=location_info.get("address"),
                ward=location_info.get("ward"),
                zone=location_info.get("zone"),
                image_path=image_url,
                annotated_image_path=result.get("annotated_image_url"),
                depth_map_path=result.get("depth_map_url"),
                source="live_capture",
                department=location_info.get("department"),
                created_by=str(current_user.id),
            )
            complaint_ids.append(str(complaint.id))

            try:
                await notify.on_complaint_created(complaint, location_info)
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Capture complaint creation failed: {e}")

    await db.commit()

    return {
        "detections": result["detections"],
        "complaints_created": len(complaint_ids),
        "complaint_ids": complaint_ids,
        "latitude": latitude,
        "longitude": longitude,
        "processing_time_ms": result["processing_time_ms"],
        "annotated_image_url": result.get("annotated_image_url"),
        "depth_map_url": result.get("depth_map_url"),
        "image_url": image_url,
    }


async def _save_frame_bytes(content: bytes, subdirectory: str):
    """Save raw frame bytes to disk."""
    import uuid
    from datetime import datetime
    from pathlib import Path
    from app.core.config import settings

    dest_dir = settings.upload_path / subdirectory
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"frame_{timestamp}_{unique_id}.jpg"
    dest = dest_dir / filename
    dest.write_bytes(content)
    return dest
