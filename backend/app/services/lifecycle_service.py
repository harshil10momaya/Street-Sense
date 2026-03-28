"""
StreetSense -- Complaint Lifecycle Manager

Manages the complete complaint lifecycle:

  OPEN -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> VERIFIED

Features:
  - Auto-assignment on creation (based on geo routing)
  - Status transition validation
  - Escalation rules (high severity auto-escalates)
  - Resolution tracking (timestamps, notes)
  - Lifecycle event hooks (for notifications)
"""

from datetime import datetime, timezone
from typing import Callable, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.complaint import Complaint, ComplaintStatus
from app.services import complaint_service, geo_service


# ===================================================================
# Status Flow Definition
# ===================================================================

STATUS_FLOW = {
    "open": {
        "allowed_next": ["assigned"],
        "description": "Complaint received, awaiting assignment",
        "auto_transition": True,  # Auto-assign on creation
    },
    "assigned": {
        "allowed_next": ["in_progress", "open"],
        "description": "Assigned to department/authority",
        "auto_transition": False,
    },
    "in_progress": {
        "allowed_next": ["resolved", "assigned"],
        "description": "Work is underway to fix the issue",
        "auto_transition": False,
    },
    "resolved": {
        "allowed_next": ["verified", "in_progress"],
        "description": "Fix completed, awaiting verification",
        "auto_transition": False,
    },
    "verified": {
        "allowed_next": [],
        "description": "Fix verified, complaint closed",
        "auto_transition": False,
    },
}


# ===================================================================
# Lifecycle Manager
# ===================================================================

class LifecycleManager:
    """Manages complaint status transitions and lifecycle events."""

    def __init__(self):
        self._event_handlers: dict[str, List[Callable]] = {
            "on_create": [],
            "on_assign": [],
            "on_start": [],
            "on_resolve": [],
            "on_verify": [],
            "on_escalate": [],
        }

    def on(self, event: str, handler: Callable):
        """Register an event handler."""
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)

    async def _emit(self, event: str, complaint: Complaint, **kwargs):
        """Emit a lifecycle event to all registered handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                result = handler(complaint, **kwargs)
                # Support async handlers
                if hasattr(result, '__await__'):
                    await result
            except Exception as e:
                logger.error(f"Event handler error ({event}): {e}")

    async def create_and_assign(
        self,
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
        image_path: str = None,
        depth_map_path: str = None,
        annotated_image_path: str = None,
        source: str = "citizen",
    ) -> Complaint:
        """
        Create a complaint AND auto-assign it based on location + issue type.

        Steps:
          1. Reverse geocode location
          2. Detect ward/zone
          3. Route to department
          4. Create complaint with all info
          5. Auto-transition to ASSIGNED if high severity
          6. Emit lifecycle events
        """
        # Step 1-3: Geo-tag and route
        location_info = geo_service.process_location(
            latitude, longitude, issue_type, severity,
        )

        # Step 4: Create complaint
        complaint = await complaint_service.create_complaint(
            db=db,
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
            address=location_info.get("address"),
            ward=location_info.get("ward"),
            zone=location_info.get("zone"),
            image_path=image_path,
            depth_map_path=depth_map_path,
            annotated_image_path=annotated_image_path,
            source=source,
            department=location_info.get("department"),
        )

        # Emit create event
        await self._emit("on_create", complaint, location_info=location_info)

        # Step 5: Auto-assign high severity complaints
        if severity in ("high",) or location_info.get("priority") in ("critical", "high"):
            assigned_to = location_info.get("assigned_to", "")
            if assigned_to:
                try:
                    complaint = await complaint_service.update_complaint_status(
                        db=db,
                        complaint_id=complaint.id,
                        new_status="assigned",
                        assigned_to=assigned_to,
                        department=location_info.get("department"),
                        notes=f"Auto-assigned: {location_info.get('priority', 'high')} priority",
                        changed_by="system-auto",
                    )
                    await self._emit("on_assign", complaint, location_info=location_info)
                    logger.info(
                        f"Auto-assigned complaint {complaint.id} to {assigned_to} "
                        f"(priority={location_info.get('priority')})"
                    )
                except ValueError:
                    pass  # Transition not valid, skip

        return complaint

    async def transition(
        self,
        db: AsyncSession,
        complaint_id: UUID,
        new_status: str,
        assigned_to: str = None,
        department: str = None,
        notes: str = None,
        changed_by: str = "system",
    ) -> Complaint:
        """
        Transition a complaint to a new status with validation.

        Raises ValueError if the transition is not allowed.
        """
        complaint = await complaint_service.update_complaint_status(
            db=db,
            complaint_id=complaint_id,
            new_status=new_status,
            assigned_to=assigned_to,
            department=department,
            notes=notes,
            changed_by=changed_by,
        )

        if complaint is None:
            raise ValueError(f"Complaint {complaint_id} not found")

        # Emit appropriate event
        event_map = {
            "assigned": "on_assign",
            "in_progress": "on_start",
            "resolved": "on_resolve",
            "verified": "on_verify",
        }
        event = event_map.get(new_status)
        if event:
            await self._emit(event, complaint)

        return complaint

    def get_status_info(self, status: str) -> dict:
        """Get information about a status."""
        info = STATUS_FLOW.get(status, {})
        return {
            "status": status,
            "description": info.get("description", "Unknown status"),
            "allowed_transitions": info.get("allowed_next", []),
        }

    def get_all_statuses(self) -> list:
        """Get info about all statuses in the lifecycle."""
        return [self.get_status_info(s) for s in STATUS_FLOW]


# Singleton lifecycle manager
lifecycle_manager = LifecycleManager()
