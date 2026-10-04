"""Unit tests for geometry validation and metrics."""

import pytest
from shapely.geometry import Polygon

from engine import geometry


def test_valid_polygon():
    geo = {
        "type": "Polygon",
        "coordinates": [
            [
                [36.8, -1.3],
                [36.9, -1.3],
                [36.9, -1.2],
                [36.8, -1.2],
                [36.8, -1.3],
            ]
        ],
    }
    validated = geometry.validate_geometry(geo)
    assert validated["type"] == "Polygon"

    area = geometry.compute_area_sq_km(geometry.shape(validated))
    assert 10.0 < area < 200.0

    centroid = geometry.compute_centroid(validated)
    assert pytest.approx(centroid["lat"], 1e-2) == -1.25
    assert pytest.approx(centroid["lng"], 1e-2) == 36.85


def test_invalid_polygon_type_rejected():
    geo = {"type": "Point", "coordinates": [36.8, -1.3]}
    with pytest.raises(geometry.GeometryError):
        geometry.validate_geometry(geo)


def test_empty_coordinates_rejected():
    geo = {"type": "Polygon", "coordinates": []}
    with pytest.raises(geometry.GeometryError):
        geometry.validate_geometry(geo)


def test_oversized_aoi_rejected():
    # Huge geometry spanning multiple continents
    geo = {
        "type": "Polygon",
        "coordinates": [
            [
                [10.0, -10.0],
                [50.0, -10.0],
                [50.0, 30.0],
                [10.0, 30.0],
                [10.0, -10.0],
            ]
        ],
    }
    with pytest.raises(geometry.GeometryError, match="exceeds the maximum"):
        geometry.validate_geometry(geo)
