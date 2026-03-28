"""
StreetSense -- API v1 Router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import complaints, geo, health, inference, lifecycle, notifications

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(complaints.router)
api_router.include_router(inference.router)
api_router.include_router(geo.router)
api_router.include_router(lifecycle.router)
api_router.include_router(notifications.router)
