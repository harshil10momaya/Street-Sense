"""
StreetSense — API v1 Router

Aggregates all endpoint routers under /api/v1 prefix.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import complaints, health

api_router = APIRouter(prefix="/api/v1")

# Health (no prefix — accessible at /api/v1/health)
api_router.include_router(health.router)

# Complaints (/api/v1/complaints/...)
api_router.include_router(complaints.router)
