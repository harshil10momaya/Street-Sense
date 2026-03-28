"""
StreetSense -- Analytics API Endpoint

Provides aggregate data for the analytics dashboard:
  - Daily complaint trends (last 30 days)
  - Average resolution time by issue type
  - Top hotspot areas
  - Severity distribution over time
  - Department performance
"""

from datetime import datetime, timedelta, timezone
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, extract, case, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.services.auth_service import get_current_user
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/daily-trends")
async def daily_trends(
    days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complaint count per day for the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Complaint.created_at).label("date"),
            Complaint.issue_type,
            func.count().label("count"),
        )
        .where(Complaint.created_at >= since)
        .group_by(func.date(Complaint.created_at), Complaint.issue_type)
        .order_by(func.date(Complaint.created_at))
    )

    rows = result.all()

    # Build date -> {type: count} map
    date_map = defaultdict(lambda: {"pothole": 0, "crack": 0, "manhole": 0, "garbage": 0, "total": 0})
    for row in rows:
        d = str(row.date)
        issue = row.issue_type
        if hasattr(issue, "value"):
            issue = issue.value
        date_map[d][issue] = row.count
        date_map[d]["total"] += row.count

    # Fill missing dates
    trend_data = []
    for i in range(days):
        date = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        entry = date_map.get(date, {"pothole": 0, "crack": 0, "manhole": 0, "garbage": 0, "total": 0})
        entry["date"] = date
        trend_data.append(entry)

    return {"days": days, "trends": trend_data}


@router.get("/resolution-time")
async def resolution_time(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Average resolution time (hours) by issue type and severity."""
    result = await db.execute(
        select(
            Complaint.issue_type,
            Complaint.severity,
            func.count().label("count"),
            func.avg(
                extract("epoch", Complaint.resolved_at - Complaint.created_at) / 3600
            ).label("avg_hours"),
        )
        .where(Complaint.resolved_at.isnot(None))
        .group_by(Complaint.issue_type, Complaint.severity)
    )

    rows = result.all()
    data = []
    for row in rows:
        issue = row.issue_type
        if hasattr(issue, "value"):
            issue = issue.value
        sev = row.severity
        if hasattr(sev, "value"):
            sev = sev.value
        data.append({
            "issue_type": issue,
            "severity": sev,
            "resolved_count": row.count,
            "avg_hours": round(float(row.avg_hours or 0), 1),
        })

    return {"resolution_times": data}


@router.get("/hotspots")
async def hotspots(
    limit: int = Query(default=10, ge=5, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top areas by complaint count (grouped by ward/zone)."""
    result = await db.execute(
        select(
            Complaint.ward,
            Complaint.zone,
            func.count().label("count"),
            func.avg(Complaint.severity_score).label("avg_severity"),
            func.avg(Complaint.latitude).label("avg_lat"),
            func.avg(Complaint.longitude).label("avg_lng"),
        )
        .where(Complaint.ward.isnot(None))
        .group_by(Complaint.ward, Complaint.zone)
        .order_by(func.count().desc())
        .limit(limit)
    )

    rows = result.all()
    data = []
    for row in rows:
        data.append({
            "ward": row.ward or "Unknown",
            "zone": row.zone or "Unknown",
            "count": row.count,
            "avg_severity": round(float(row.avg_severity or 0), 3),
            "latitude": round(float(row.avg_lat or 0), 6),
            "longitude": round(float(row.avg_lng or 0), 6),
        })

    return {"hotspots": data}


@router.get("/severity-distribution")
async def severity_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Severity breakdown by issue type."""
    result = await db.execute(
        select(
            Complaint.issue_type,
            Complaint.severity,
            func.count().label("count"),
        )
        .group_by(Complaint.issue_type, Complaint.severity)
    )

    rows = result.all()
    data = defaultdict(lambda: {"low": 0, "medium": 0, "high": 0, "total": 0})
    for row in rows:
        issue = row.issue_type
        if hasattr(issue, "value"):
            issue = issue.value
        sev = row.severity
        if hasattr(sev, "value"):
            sev = sev.value
        data[issue][sev] = row.count
        data[issue]["total"] += row.count

    return {"distribution": dict(data)}


@router.get("/department-performance")
async def department_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complaints per department with resolution rates."""
    result = await db.execute(
        select(
            Complaint.department,
            func.count().label("total"),
            func.count(Complaint.resolved_at).label("resolved"),
        )
        .where(Complaint.department.isnot(None))
        .group_by(Complaint.department)
        .order_by(func.count().desc())
    )

    rows = result.all()
    data = []
    for row in rows:
        total = row.total
        resolved = row.resolved
        rate = round(resolved / total * 100, 1) if total > 0 else 0
        data.append({
            "department": row.department,
            "total": total,
            "resolved": resolved,
            "resolution_rate": rate,
        })

    return {"departments": data}
