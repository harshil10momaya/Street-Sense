"""
StreetSense -- Complaints API Endpoints

Endpoints:
  POST   /complaints/upload          Upload image -> AI inference -> create complaints
  GET    /complaints/                List complaints (filtered, paginated)
  GET    /complaints/{id}            Get single complaint
  PATCH  /complaints/{id}/status     Update complaint status
  GET    /complaints/{id}/history    Get complaint status history
  GET    /complaints/stats/dashboard  Dashboard aggregate stats
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintListResponse,
    ComplaintResponse,
    ComplaintUpdate,
    HistoryEntry,
    InferenceResponse,
)
from app.services import complaint_service, ai_service, geo_service
from app.utils.file_utils import (
    get_relative_url,
    read_image_from_upload,
    save_upload,
    validate_image_file,
)

router = APIRouter(prefix="/complaints", tags=["complaints"])


# ===================================================================
# POST /complaints/upload -- Upload image, run AI, create complaints
# ===================================================================

@router.post("/upload", response_model=InferenceResponse)
async def upload_and_detect(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    source: str = Form(default="citizen"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload an image for AI-powered road damage detection.

    1. Validates and saves the uploaded image
    2. Runs YOLO + MiDaS inference pipeline
    3. Creates a complaint for each detection
    4. Returns detection results with annotated image URLs
    """
    # Validate file
    error = validate_image_file(file)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Save uploaded file
    saved_path = await save_upload(file, subdirectory="originals", prefix="upload")
    image_url = get_relative_url(saved_path)

    # Read image bytes for inference
    await file.seek(0)
    content = await file.read()

    try:
        image = read_image_from_upload(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Run AI inference
    try:
        inference_result = await ai_service.run_inference(image)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail="AI inference failed")

    # Create a complaint for each detection (with geo-tagging + routing)
    for det in inference_result["detections"]:
        bbox = det["bbox"]

        # Geo-tag and route
        location_info = geo_service.process_location(
            latitude=latitude,
            longitude=longitude,
            issue_type=det["issue_type"],
            severity=det["severity"],
        )

        await complaint_service.create_complaint(
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
            depth_map_path=inference_result.get("depth_map_url"),
            annotated_image_path=inference_result.get("annotated_image_url"),
            source=source,
            department=location_info.get("department"),
        )

    await db.commit()

    return InferenceResponse(
        image_id=inference_result["image_id"],
        detections=[
            {
                "issue_type": d["issue_type"],
                "confidence": d["confidence"],
                "bbox": d["bbox"],
                "depth_value": d.get("depth_value"),
                "severity": d["severity"],
                "severity_score": d["severity_score"],
            }
            for d in inference_result["detections"]
        ],
        annotated_image_url=inference_result.get("annotated_image_url"),
        depth_map_url=inference_result.get("depth_map_url"),
        processing_time_ms=inference_result["processing_time_ms"],
    )


# ===================================================================
# GET /complaints/ -- List complaints
# ===================================================================

@router.get("/", response_model=ComplaintListResponse)
async def list_complaints(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    issue_type: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    List complaints with filtering and pagination.

    Filters: status, severity, issue_type, source
    Sort: any field (default: created_at desc)
    """
    complaints, total = await complaint_service.list_complaints(
        db=db,
        page=page,
        per_page=per_page,
        status=status,
        severity=severity,
        issue_type=issue_type,
        source=source,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return ComplaintListResponse(
        total=total,
        page=page,
        per_page=per_page,
        complaints=[ComplaintResponse.model_validate(c) for c in complaints],
    )


# ===================================================================
# GET /complaints/stats/dashboard -- Dashboard stats
# ===================================================================

@router.get("/stats/dashboard")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Get aggregate stats for the dashboard:
    - Total complaints
    - Recent (24h)
    - By status, severity, issue type
    """
    stats = await complaint_service.get_dashboard_stats(db)
    return stats


# ===================================================================
# GET /complaints/{id} -- Get single complaint
# ===================================================================

@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    complaint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single complaint by ID."""
    complaint = await complaint_service.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return ComplaintResponse.model_validate(complaint)


# ===================================================================
# PATCH /complaints/{id}/status -- Update status
# ===================================================================

@router.patch("/{complaint_id}/status", response_model=ComplaintResponse)
async def update_status(
    complaint_id: uuid.UUID,
    body: ComplaintUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a complaint's status.

    Valid transitions:
      open -> assigned
      assigned -> in_progress | open
      in_progress -> resolved | assigned
      resolved -> verified | in_progress
      verified -> (terminal)
    """
    try:
        complaint = await complaint_service.update_complaint_status(
            db=db,
            complaint_id=complaint_id,
            new_status=body.status,
            assigned_to=body.assigned_to,
            department=body.department,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    await db.commit()
    return ComplaintResponse.model_validate(complaint)


# ===================================================================
# GET /complaints/{id}/history -- Status history
# ===================================================================

@router.get("/{complaint_id}/history", response_model=list[HistoryEntry])
async def get_history(
    complaint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the full status change history for a complaint."""
    # Verify complaint exists
    complaint = await complaint_service.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    history = await complaint_service.get_complaint_history(db, complaint_id)
    return [HistoryEntry.model_validate(h) for h in history]
