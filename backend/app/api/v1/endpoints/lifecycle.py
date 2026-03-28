"""
StreetSense -- Lifecycle API Endpoints

Endpoints:
  GET  /lifecycle/statuses           List all statuses with allowed transitions
  GET  /lifecycle/statuses/{status}  Get info about a specific status
  POST /lifecycle/escalate/{id}      Escalate a complaint (force high priority)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.complaint import ComplaintResponse
from app.services import complaint_service
from app.services.lifecycle_service import lifecycle_manager

router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])


@router.get("/statuses")
async def list_statuses():
    """Get all complaint statuses with their allowed transitions."""
    return {
        "statuses": lifecycle_manager.get_all_statuses(),
        "flow": "open -> assigned -> in_progress -> resolved -> verified",
    }


@router.get("/statuses/{status}")
async def get_status_info(status: str):
    """Get info about a specific status including allowed transitions."""
    info = lifecycle_manager.get_status_info(status)
    if info["description"] == "Unknown status":
        raise HTTPException(status_code=404, detail=f"Unknown status: {status}")
    return info


@router.post("/escalate/{complaint_id}", response_model=ComplaintResponse)
async def escalate_complaint(
    complaint_id: UUID,
    notes: str = "Escalated by authority",
    db: AsyncSession = Depends(get_db),
):
    """
    Escalate a complaint -- force-assign it to department head.
    Works from any status except 'verified'.
    """
    complaint = await complaint_service.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    current_status = (
        complaint.status.value
        if hasattr(complaint.status, "value")
        else complaint.status
    )

    if current_status == "verified":
        raise HTTPException(status_code=400, detail="Cannot escalate verified complaints")

    # If open, assign first
    if current_status == "open":
        complaint = await complaint_service.update_complaint_status(
            db=db,
            complaint_id=complaint_id,
            new_status="assigned",
            notes=f"Escalated: {notes}",
            changed_by="system-escalation",
        )

    # If assigned, move to in_progress
    current_status = (
        complaint.status.value
        if hasattr(complaint.status, "value")
        else complaint.status
    )
    if current_status == "assigned":
        complaint = await complaint_service.update_complaint_status(
            db=db,
            complaint_id=complaint_id,
            new_status="in_progress",
            notes=f"Escalated to in_progress: {notes}",
            changed_by="system-escalation",
        )

    await db.commit()
    return ComplaintResponse.model_validate(complaint)
