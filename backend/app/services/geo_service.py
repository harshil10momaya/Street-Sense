"""
StreetSense -- Geo-Tagging & Smart Routing Service

Handles:
  1. Reverse geocoding (lat/lng -> address, ward, zone)
  2. Department mapping (issue type + location -> responsible department)
  3. Authority assignment (department -> contact person)

Uses geopy for geocoding with caching to avoid rate limits.
"""

import functools
from typing import Optional, Tuple
from loguru import logger


# ===================================================================
# Reverse Geocoding
# ===================================================================

# Simple in-memory cache for geocoding results
_geocode_cache = {}


def reverse_geocode(latitude: float, longitude: float) -> dict:
    """
    Convert lat/lng coordinates to a human-readable address.

    Returns:
        {
            "address": "123 Main St, Chennai, Tamil Nadu 600001",
            "road": "Main Street",
            "area": "T. Nagar",
            "city": "Chennai",
            "district": "Chennai",
            "state": "Tamil Nadu",
            "postcode": "600001",
            "country": "India",
            "raw": {...}  # Full geocoder response
        }
    """
    cache_key = f"{latitude:.5f},{longitude:.5f}"
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

        geolocator = Nominatim(
            user_agent="streetsense-app",
            timeout=10,
        )

        location = geolocator.reverse(
            f"{latitude}, {longitude}",
            exactly_one=True,
            language="en",
        )

        if location is None:
            result = _empty_geo_result(latitude, longitude)
            _geocode_cache[cache_key] = result
            return result

        raw = location.raw.get("address", {})

        result = {
            "address": location.address or "",
            "road": raw.get("road", raw.get("street", "")),
            "area": raw.get("suburb", raw.get("neighbourhood", raw.get("village", ""))),
            "city": raw.get("city", raw.get("town", raw.get("municipality", ""))),
            "district": raw.get("county", raw.get("state_district", "")),
            "state": raw.get("state", ""),
            "postcode": raw.get("postcode", ""),
            "country": raw.get("country", ""),
            "raw": raw,
        }

        _geocode_cache[cache_key] = result
        logger.debug(f"Geocoded ({latitude},{longitude}) -> {result['area']}, {result['city']}")
        return result

    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        logger.warning(f"Geocoding failed (timeout): {e}")
        return _empty_geo_result(latitude, longitude)
    except ImportError:
        logger.warning("geopy not installed. Install: pip install geopy")
        return _empty_geo_result(latitude, longitude)
    except Exception as e:
        logger.warning(f"Geocoding failed: {e}")
        return _empty_geo_result(latitude, longitude)


def _empty_geo_result(lat: float, lng: float) -> dict:
    return {
        "address": f"Location ({lat:.4f}, {lng:.4f})",
        "road": "",
        "area": "",
        "city": "",
        "district": "",
        "state": "",
        "postcode": "",
        "country": "",
        "raw": {},
    }


# ===================================================================
# Ward & Zone Detection
# ===================================================================

# Chennai zone mapping (example -- extend for your city)
# In production, this would use GIS boundaries (shapefiles/PostGIS)
ZONE_MAPPING = {
    "T. Nagar": {"ward": "Ward 123", "zone": "Zone 10 - Kodambakkam"},
    "Adyar": {"ward": "Ward 173", "zone": "Zone 13 - Adyar"},
    "Anna Nagar": {"ward": "Ward 98", "zone": "Zone 8 - Anna Nagar"},
    "Mylapore": {"ward": "Ward 119", "zone": "Zone 9 - Teynampet"},
    "Tambaram": {"ward": "Ward 191", "zone": "Zone 15 - Sholinganallur"},
    "Guindy": {"ward": "Ward 155", "zone": "Zone 12 - Alandur"},
    "Velachery": {"ward": "Ward 180", "zone": "Zone 14 - Perungudi"},
    "Nungambakkam": {"ward": "Ward 108", "zone": "Zone 9 - Teynampet"},
    "Chromepet": {"ward": "Ward 193", "zone": "Zone 15 - Sholinganallur"},
    "Porur": {"ward": "Ward 149", "zone": "Zone 11 - Valasaravakkam"},
}

# Fallback zone assignment by postcode prefix
POSTCODE_ZONES = {
    "6000": "Zone 1-5 - North Chennai",
    "6001": "Zone 6-10 - Central Chennai",
    "6002": "Zone 11-15 - South Chennai",
}


def detect_ward_zone(geo_info: dict) -> Tuple[str, str]:
    """
    Determine the ward and zone from geocoding results.

    Args:
        geo_info: Result from reverse_geocode()

    Returns:
        (ward, zone)
    """
    area = geo_info.get("area", "")
    postcode = geo_info.get("postcode", "")

    # Try area-based lookup first
    if area in ZONE_MAPPING:
        mapping = ZONE_MAPPING[area]
        return mapping["ward"], mapping["zone"]

    # Fallback: postcode-based
    if postcode:
        prefix = postcode[:4]
        zone = POSTCODE_ZONES.get(prefix, "Unknown Zone")
        return f"Ward (auto-{postcode})", zone

    return "Unknown Ward", "Unknown Zone"


# ===================================================================
# Department Routing
# ===================================================================

# Maps issue type to responsible department
DEPARTMENT_MAPPING = {
    "pothole": {
        "department": "Roads & Infrastructure Department",
        "sub_department": "Road Maintenance Division",
        "priority_multiplier": 1.5,  # Potholes get higher priority
    },
    "crack": {
        "department": "Roads & Infrastructure Department",
        "sub_department": "Road Inspection Division",
        "priority_multiplier": 1.0,
    },
    "manhole": {
        "department": "Water & Sewerage Department",
        "sub_department": "Sewerage Maintenance Division",
        "priority_multiplier": 2.0,  # Open manholes are critical safety hazards
    },
    "garbage": {
        "department": "Solid Waste Management Department",
        "sub_department": "Collection & Disposal Division",
        "priority_multiplier": 0.8,
    },
}

# Zone-based authority contacts (example)
ZONE_AUTHORITIES = {
    "Zone 10 - Kodambakkam": {
        "engineer": "Mr. Rajesh Kumar",
        "email": "rajesh.k@corporation.gov",
        "phone": "+91-44-2834-XXXX",
    },
    "Zone 13 - Adyar": {
        "engineer": "Ms. Priya Sharma",
        "email": "priya.s@corporation.gov",
        "phone": "+91-44-2441-XXXX",
    },
    "Zone 9 - Teynampet": {
        "engineer": "Mr. Suresh Babu",
        "email": "suresh.b@corporation.gov",
        "phone": "+91-44-2435-XXXX",
    },
}


def route_complaint(
    issue_type: str,
    severity: str,
    ward: str = "",
    zone: str = "",
) -> dict:
    """
    Determine which department and authority should handle a complaint.

    Args:
        issue_type: pothole, crack, manhole, garbage
        severity: low, medium, high
        ward: Ward identifier
        zone: Zone identifier

    Returns:
        {
            "department": "Roads & Infrastructure Department",
            "sub_department": "Road Maintenance Division",
            "assigned_to": "Mr. Rajesh Kumar",
            "contact_email": "rajesh.k@corporation.gov",
            "contact_phone": "+91-44-2834-XXXX",
            "priority": "high",
        }
    """
    # Get department for this issue type
    dept_info = DEPARTMENT_MAPPING.get(issue_type, {
        "department": "General Maintenance Department",
        "sub_department": "General Division",
        "priority_multiplier": 1.0,
    })

    # Get zone authority
    authority = ZONE_AUTHORITIES.get(zone, {
        "engineer": "Unassigned (Zone not mapped)",
        "email": "",
        "phone": "",
    })

    # Calculate priority based on severity + issue type multiplier
    severity_scores = {"low": 1, "medium": 2, "high": 3}
    base_score = severity_scores.get(severity, 1)
    adjusted_score = base_score * dept_info["priority_multiplier"]

    if adjusted_score >= 4.0:
        priority = "critical"
    elif adjusted_score >= 2.5:
        priority = "high"
    elif adjusted_score >= 1.5:
        priority = "medium"
    else:
        priority = "low"

    return {
        "department": dept_info["department"],
        "sub_department": dept_info["sub_department"],
        "assigned_to": authority.get("engineer", ""),
        "contact_email": authority.get("email", ""),
        "contact_phone": authority.get("phone", ""),
        "priority": priority,
        "ward": ward,
        "zone": zone,
    }


def process_location(
    latitude: float,
    longitude: float,
    issue_type: str,
    severity: str,
) -> dict:
    """
    Full location processing pipeline:
      1. Reverse geocode lat/lng -> address
      2. Detect ward/zone
      3. Route to department + authority

    Returns combined result with all location and routing info.
    """
    # Step 1: Reverse geocode
    geo_info = reverse_geocode(latitude, longitude)

    # Step 2: Ward/Zone detection
    ward, zone = detect_ward_zone(geo_info)

    # Step 3: Route to department
    routing = route_complaint(issue_type, severity, ward, zone)

    return {
        "address": geo_info["address"],
        "road": geo_info["road"],
        "area": geo_info["area"],
        "city": geo_info["city"],
        "state": geo_info["state"],
        "postcode": geo_info["postcode"],
        "ward": ward,
        "zone": zone,
        "department": routing["department"],
        "sub_department": routing["sub_department"],
        "assigned_to": routing["assigned_to"],
        "contact_email": routing["contact_email"],
        "contact_phone": routing["contact_phone"],
        "priority": routing["priority"],
    }
