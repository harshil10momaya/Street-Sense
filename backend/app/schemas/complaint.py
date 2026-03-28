"""
StreetSense — Pydantic Schemas

Request/response models for the API layer.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Enums (mirror ORM enums for serialization) ───

class IssueTypeEnum(str):
    POTHOLE = "pothole"
    CRACK = "crack"
    GARBAGE = "garbage"
    MANHOLE = "manhole"


class SeverityEnum(str):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StatusEnum(str):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    VERIFIED = "verified"


# ─── Detection Result (from AI pipeline) ───

class BoundingBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class DetectionResult(BaseModel):
    """Single detection from YOLO + MiDaS pipeline."""
    issue_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox
    depth_value: Optional[float] = None
    severity: str
    severity_score: float = Field(ge=0.0, le=1.0)


class InferenceResponse(BaseModel):
    """Full response from running inference on an image."""
    image_id: str
    detections: List[DetectionResult]
    annotated_image_url: Optional[str] = None
    depth_map_url: Optional[str] = None
    processing_time_ms: float


# ─── Complaint Schemas ───

class ComplaintCreate(BaseModel):
    """Manual complaint submission by a citizen."""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    issue_type: Optional[str] = None  # Can be auto-detected
    description: Optional[str] = None
    source: str = "citizen"


class ComplaintResponse(BaseModel):
    """Full complaint record returned to clients."""
    id: UUID
    issue_type: str
    confidence: float
    severity: str
    severity_score: float
    depth_value: Optional[float]
    latitude: float
    longitude: float
    address: Optional[str]
    ward: Optional[str]
    zone: Optional[str]
    image_path: Optional[str]
    depth_map_path: Optional[str]
    annotated_image_path: Optional[str]
    source: str
    created_by: Optional[UUID] = None
    status: str
    assigned_to: Optional[str]
    department: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ComplaintUpdate(BaseModel):
    """Status update for a complaint."""
    status: str
    assigned_to: Optional[str] = None
    department: Optional[str] = None
    notes: Optional[str] = None


class ComplaintListResponse(BaseModel):
    """Paginated list of complaints."""
    total: int
    page: int
    per_page: int
    complaints: List[ComplaintResponse]


# ─── History ───

class HistoryEntry(BaseModel):
    """Single status change record."""
    id: UUID
    complaint_id: UUID
    previous_status: Optional[str]
    new_status: str
    changed_by: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Health Check ───

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    ai_models_loaded: bool = False
