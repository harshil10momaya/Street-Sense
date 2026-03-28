"""
StreetSense -- Complaint Service

All database operations for complaints and history.
Called by API endpoints, never directly by routes.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.complaint import Complaint, ComplaintStatus, IssueType, Severity
from app.models.history import ComplaintHistory


async def create_complaint(
    db: AsyncSession,
    issue_type: str,
    confidence: float,
    severity: str,
    severity_score: float,
    latitude: float,
    longitude: float,
    depth_value: float = None,
    bbox_x: float = None,
    bbox_y: float = None,
    bbox_w: float = None,
    bbox_h: float = None,
    address: str = None,
    ward: str = None,
    zone: str = None,
    image_path: str = None,
    depth_map_path: str = None,
    annotated_image_path: str = None,
    source: str = "citizen",
    department: str = None,
) -> Complaint:
    """Create a new complaint and record initial history."""

    complaint = Complaint(
        id=uuid.uuid4(),
        issue_type=issue_type,
        confidence=confidence,
        severity=severity,
        severity_score=severity_score,
        depth_value=depth_value,
        bbox_x=bbox_x,
        bbox_y=bbox_y,
        bbox_w=bbox_w,
        bbox_h=bbox_h,
        latitude=latitude,
        longitude=longitude,
        address=address,
        ward=ward,
        zone=zone,
        image_path=image_path,
        depth_map_path=depth_map_path,
        annotated_image_path=annotated_image_path,
        source=source,
        status=ComplaintStatus.OPEN,
        department=department,
    )

    db.add(complaint)

    # Record initial history
    history = ComplaintHistory(
        complaint_id=complaint.id,
        previous_status=None,
        new_status=ComplaintStatus.OPEN.value,
        changed_by="system",
        notes=f"Complaint created via {source}",
    )
    db.add(history)

    await db.flush()
    await db.refresh(complaint)

    logger.info(f"Created complaint {complaint.id}: {issue_type}, severity={severity}")
    return complaint


async def get_complaint(db: AsyncSession, complaint_id: uuid.UUID) -> Optional[Complaint]:
    """Get a single complaint by ID."""
    result = await db.execute(
        select(Complaint).where(Complaint.id == complaint_id)
    )
    return result.scalar_one_or_none()


async def list_complaints(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    status: str = None,
    severity: str = None,
    issue_type: str = None,
    source: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Tuple[List[Complaint], int]:
    """
    List complaints with filtering and pagination.

    Returns:
        (complaints_list, total_count)
    """
    query = select(Complaint)
    count_query = select(func.count()).select_from(Complaint)

    # Apply filters
    if status:
        query = query.where(Complaint.status == status)
        count_query = count_query.where(Complaint.status == status)
    if severity:
        query = query.where(Complaint.severity == severity)
        count_query = count_query.where(Complaint.severity == severity)
    if issue_type:
        query = query.where(Complaint.issue_type == issue_type)
        count_query = count_query.where(Complaint.issue_type == issue_type)
    if source:
        query = query.where(Complaint.source == source)
        count_query = count_query.where(Complaint.source == source)

    # Sort
    sort_col = getattr(Complaint, sort_by, Complaint.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Count total
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    complaints = list(result.scalars().all())

    return complaints, total


async def update_complaint_status(
    db: AsyncSession,
    complaint_id: uuid.UUID,
    new_status: str,
    assigned_to: str = None,
    department: str = None,
    notes: str = None,
    changed_by: str = "system",
) -> Optional[Complaint]:
    """Update complaint status and record history."""

    complaint = await get_complaint(db, complaint_id)
    if not complaint:
        return None

    old_status = complaint.status.value if isinstance(complaint.status, ComplaintStatus) else complaint.status

    # Validate status transition
    valid = validate_status_transition(old_status, new_status)
    if not valid:
        raise ValueError(
            f"Invalid status transition: {old_status} -> {new_status}. "
            f"Allowed: {get_allowed_transitions(old_status)}"
        )

    # Update complaint
    complaint.status = new_status
    if assigned_to is not None:
        complaint.assigned_to = assigned_to
    if department is not None:
        complaint.department = department
    complaint.updated_at = datetime.now(timezone.utc)

    if new_status == ComplaintStatus.RESOLVED.value:
        complaint.resolved_at = datetime.now(timezone.utc)

    # Record history
    history = ComplaintHistory(
        complaint_id=complaint_id,
        previous_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        notes=notes,
    )
    db.add(history)

    await db.flush()
    await db.refresh(complaint)

    logger.info(f"Complaint {complaint_id}: {old_status} -> {new_status}")
    return complaint


async def get_complaint_history(
    db: AsyncSession,
    complaint_id: uuid.UUID,
) -> List[ComplaintHistory]:
    """Get full status history for a complaint."""
    result = await db.execute(
        select(ComplaintHistory)
        .where(ComplaintHistory.complaint_id == complaint_id)
        .order_by(ComplaintHistory.created_at.asc())
    )
    return list(result.scalars().all())


async def get_dashboard_stats(db: AsyncSession) -> dict:
    """Get aggregate stats for the dashboard."""

    # Total complaints
    total_result = await db.execute(select(func.count()).select_from(Complaint))
    total = total_result.scalar()

    # By status
    status_query = (
        select(Complaint.status, func.count())
        .group_by(Complaint.status)
    )
    status_result = await db.execute(status_query)
    by_status = {str(row[0].value if hasattr(row[0], 'value') else row[0]): row[1] for row in status_result}

    # By severity
    severity_query = (
        select(Complaint.severity, func.count())
        .group_by(Complaint.severity)
    )
    severity_result = await db.execute(severity_query)
    by_severity = {str(row[0].value if hasattr(row[0], 'value') else row[0]): row[1] for row in severity_result}

    # By issue type
    type_query = (
        select(Complaint.issue_type, func.count())
        .group_by(Complaint.issue_type)
    )
    type_result = await db.execute(type_query)
    by_type = {str(row[0].value if hasattr(row[0], 'value') else row[0]): row[1] for row in type_result}

    # Recent (last 24 hours)
    yesterday = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    recent_result = await db.execute(
        select(func.count()).select_from(Complaint)
        .where(Complaint.created_at >= yesterday)
    )
    recent = recent_result.scalar()

    return {
        "total": total,
        "recent_24h": recent,
        "by_status": by_status,
        "by_severity": by_severity,
        "by_type": by_type,
    }


# -- Status transition rules --

ALLOWED_TRANSITIONS = {
    "open": ["assigned"],
    "assigned": ["in_progress", "open"],
    "in_progress": ["resolved", "assigned"],
    "resolved": ["verified", "in_progress"],
    "verified": [],  # Terminal state
}


def validate_status_transition(current: str, new: str) -> bool:
    """Check if a status transition is valid."""
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    return new in allowed


def get_allowed_transitions(current: str) -> list:
    """Get valid next statuses from current status."""
    return ALLOWED_TRANSITIONS.get(current, [])
