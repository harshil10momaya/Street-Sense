"""
StreetSense -- Geo-Tagging API Endpoint

Endpoints:
  GET  /geo/reverse    Reverse geocode lat/lng to address
  GET  /geo/route      Get department routing for a location + issue type
"""

from typing import Optional

from fastapi import APIRouter, Query
from loguru import logger

from app.services import geo_service

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/reverse")
async def reverse_geocode(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    """
    Reverse geocode coordinates to an address with ward/zone info.

    Example: GET /api/v1/geo/reverse?latitude=13.0827&longitude=80.2707
    """
    geo_info = geo_service.reverse_geocode(latitude, longitude)
    ward, zone = geo_service.detect_ward_zone(geo_info)

    return {
        "latitude": latitude,
        "longitude": longitude,
        "address": geo_info["address"],
        "road": geo_info["road"],
        "area": geo_info["area"],
        "city": geo_info["city"],
        "state": geo_info["state"],
        "postcode": geo_info["postcode"],
        "ward": ward,
        "zone": zone,
    }


@router.get("/route")
async def get_routing(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    issue_type: str = Query(..., regex="^(pothole|crack|manhole|garbage)$"),
    severity: str = Query(default="medium", regex="^(low|medium|high)$"),
):
    """
    Get full location + department routing for a given location and issue type.

    Example: GET /api/v1/geo/route?latitude=13.0827&longitude=80.2707&issue_type=pothole&severity=high
    """
    result = geo_service.process_location(latitude, longitude, issue_type, severity)
    result["latitude"] = latitude
    result["longitude"] = longitude
    result["issue_type"] = issue_type
    result["severity"] = severity
    return result
