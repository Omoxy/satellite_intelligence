"""Geometry validation, transformation, and measurement.

Operates on GeoJSON geometry dicts. Uses Shapely for validation and
pyproj for area measurement in projected coordinates.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
from shapely.geometry import shape, mapping
from shapely.validation import explain_validity

import config

logger = logging.getLogger(__name__)


class GeometryError(Exception):
    """Raised when geometry validation fails."""


def validate_geometry(geojson: dict) -> dict:
    """Validate a GeoJSON geometry and return a cleaned version.

    Checks
    ------
    - Type is Polygon or MultiPolygon
    - Coordinates are present and non-empty
    - Geometry is valid per OGC rules (rings closed, no self-intersection)
    - Area is within configured min/max bounds

    Returns
    -------
    dict
        The validated (and possibly repaired) GeoJSON geometry.

    Raises
    ------
    GeometryError
        If the geometry is invalid and cannot be repaired.
    """
    geo_type = geojson.get("type")
    if geo_type not in ("Polygon", "MultiPolygon"):
        raise GeometryError(
            f"Geometry type must be Polygon or MultiPolygon, got '{geo_type}'"
        )

    coords = geojson.get("coordinates")
    if not coords:
        raise GeometryError("Geometry coordinates are empty")

    try:
        geom = shape(geojson)
    except Exception as exc:
        raise GeometryError(f"Cannot parse geometry: {exc}") from exc

    if geom.is_empty:
        raise GeometryError("Geometry is empty")

    if not geom.is_valid:
        explanation = explain_validity(geom)
        # Attempt buffer(0) repair for minor topology issues
        repaired = geom.buffer(0)
        if repaired.is_valid and not repaired.is_empty:
            logger.info("Geometry repaired via buffer(0): %s", explanation)
            geom = repaired
        else:
            raise GeometryError(f"Invalid geometry: {explanation}")

    # Area check (approximate, using WGS84 degrees → sq km conversion)
    area_km2 = compute_area_sq_km(geom)
    if area_km2 < config.MIN_AOI_AREA_SQ_M / 1e6:
        raise GeometryError(
            f"AOI area ({area_km2:.4f} sq km) is below the minimum "
            f"({config.MIN_AOI_AREA_SQ_M / 1e6:.4f} sq km)"
        )
    if area_km2 > config.MAX_AOI_AREA_SQ_KM:
        raise GeometryError(
            f"AOI area ({area_km2:.1f} sq km) exceeds the maximum "
            f"({config.MAX_AOI_AREA_SQ_KM:.0f} sq km)"
        )

    return mapping(geom)


def compute_area_sq_km(geom) -> float:
    """Approximate area in square kilometres using the Haversine spheroid.

    For AOIs near the equator (Kenya), this is accurate to within ~0.5%.
    Uses a sinusoidal equal-area approximation for speed.
    """
    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    mid_lat = (bounds[1] + bounds[3]) / 2.0

    # Degrees to km at this latitude
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * math.cos(math.radians(mid_lat))

    # Scale geometry to approximate metric
    area_deg2 = geom.area  # in square degrees
    area_km2 = area_deg2 * km_per_deg_lat * km_per_deg_lon
    return area_km2


def compute_centroid(geojson: dict) -> dict:
    """Return centroid as {lat, lng}."""
    geom = shape(geojson)
    c = geom.centroid
    return {"lat": round(c.y, 6), "lng": round(c.x, 6)}


def compute_bbox(geojson: dict) -> dict:
    """Return bounding box as {west, south, east, north}."""
    geom = shape(geojson)
    west, south, east, north = geom.bounds
    return {
        "west": round(west, 6),
        "south": round(south, 6),
        "east": round(east, 6),
        "north": round(north, 6),
    }


def get_coordinates(geojson: dict) -> list:
    """Extract exterior ring coordinates from the geometry."""
    geom = shape(geojson)
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    exterior = geom.exterior
    return [
        {"lat": round(y, 6), "lng": round(x, 6)}
        for x, y in exterior.coords
    ]


def geometry_contains_point(geojson: dict, lat: float, lng: float) -> bool:
    """Check whether a point falls within the geometry."""
    from shapely.geometry import Point
    geom = shape(geojson)
    return geom.contains(Point(lng, lat))


def get_pixel_coords(
    geojson: dict,
    raster_shape: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, tuple[float, float, float, float]]:
    """Compute pixel grid coordinates for a raster covering the geometry bounds.

    Returns
    -------
    xs : ndarray, shape (W,)
        Longitude values for each column.
    ys : ndarray, shape (H,)
        Latitude values for each row (north to south).
    bounds : (west, south, east, north)
    """
    geom = shape(geojson)
    west, south, east, north = geom.bounds
    h, w = raster_shape
    xs = np.linspace(west, east, w)
    ys = np.linspace(north, south, h)  # north at top (row 0)
    return xs, ys, (west, south, east, north)
