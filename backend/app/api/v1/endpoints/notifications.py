"""
StreetSense -- Notifications API Endpoint

Endpoints:
  GET  /notifications/           List recent notifications
  GET  /notifications/unread     Get unread count
  POST /notifications/{id}/read  Mark notification as read
"""

from fastapi import APIRouter, Query

from app.services.notification_service import (
    get_notifications,
    get_unread_count,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
async def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    unread_only: bool = Query(default=False),
):
    """Get recent notifications."""
    notifications = get_notifications(limit=limit, unread_only=unread_only)
    return {
        "notifications": notifications,
        "total": len(notifications),
        "unread_count": get_unread_count(),
    }


@router.get("/unread")
async def unread_count():
    """Get count of unread notifications."""
    return {"unread_count": get_unread_count()}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str):
    """Mark a notification as read."""
    success = mark_notification_read(notification_id)
    if not success:
        return {"success": False, "message": "Notification not found"}
    return {"success": True}
