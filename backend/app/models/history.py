"""
StreetSense — Complaint History ORM Model

Tracks every status change in a complaint's lifecycle.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class ComplaintHistory(Base):
    """Audit trail for complaint status transitions."""

    __tablename__ = "complaint_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    changed_by = Column(String(200), nullable=True)  # User or system
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ComplaintHistory(complaint={self.complaint_id}, "
            f"{self.previous_status} → {self.new_status})>"
        )
