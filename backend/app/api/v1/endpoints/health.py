"""
StreetSense — Health Check Endpoint
"""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.complaint import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        ai_models_loaded=False,  # Will be updated in Phase 4
    )
