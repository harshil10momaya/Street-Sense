"""
StreetSense — Complaints Endpoints

Upload images, run inference, manage complaints.
Full implementation in Phase 6.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.get("/")
async def list_complaints():
    """List all complaints (paginated). Implemented in Phase 6."""
    return {
        "message": "Complaints endpoint ready. Full implementation in Phase 6.",
        "total": 0,
        "complaints": [],
    }
