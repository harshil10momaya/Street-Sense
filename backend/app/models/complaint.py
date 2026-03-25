"""
StreetSense — Complaint ORM Model

Represents a detected road issue or citizen-submitted complaint.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class IssueType(str, enum.Enum):
    """Types of road issues detected."""
    POTHOLE = "pothole"
    CRACK = "crack"
    GARBAGE = "garbage"
    MANHOLE = "manhole"


class Severity(str, enum.Enum):
    """Depth-aware severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ComplaintStatus(str, enum.Enum):
    """Complaint lifecycle states."""
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    VERIFIED = "verified"


class Complaint(Base):
    """Core complaint entity."""

    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Detection data
    issue_type = Column(Enum(IssueType), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    severity = Column(Enum(Severity), nullable=False, index=True)
    severity_score = Column(Float, nullable=False)  # 0.0 — 1.0
    depth_value = Column(Float, nullable=True)       # Average MiDaS depth

    # Bounding box (from YOLO)
    bbox_x = Column(Float, nullable=True)
    bbox_y = Column(Float, nullable=True)
    bbox_w = Column(Float, nullable=True)
    bbox_h = Column(Float, nullable=True)

    # Location
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    address = Column(Text, nullable=True)
    ward = Column(String(100), nullable=True)
    zone = Column(String(100), nullable=True)

    # Media
    image_path = Column(String(500), nullable=True)
    depth_map_path = Column(String(500), nullable=True)
    annotated_image_path = Column(String(500), nullable=True)

    # Source
    source = Column(String(50), default="camera")  # camera | citizen | feed

    # Lifecycle
    status = Column(
        Enum(ComplaintStatus),
        nullable=False,
        default=ComplaintStatus.OPEN,
        index=True,
    )
    assigned_to = Column(String(200), nullable=True)
    department = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Complaint(id={self.id}, type={self.issue_type}, "
            f"severity={self.severity}, status={self.status})>"
        )
