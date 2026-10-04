"""Security and input validation tests."""

import pytest
from fastapi.testclient import TestClient

import database
from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_security_headers_present(client):
    res = client.get("/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin" in res.headers.get("Referrer-Policy", "")


def test_sql_injection_attempt_in_area_name(client):
    """SQL injection in string fields must be safely handled via parameterised queries."""
    payload = {
        "name": "Robert'); DROP TABLE areas_of_interest;--",
        "geometry": {
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
        },
    }
    res = client.post("/api/areas", json=payload)
    assert res.status_code == 201

    # Verify table is intact
    with database.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM areas_of_interest").fetchone()[0]
        assert count > 0


def test_protect_predefined_areas_from_deletion(client):
    """Predefined study areas cannot be deleted."""
    res = client.delete("/api/areas/predefined-nairobi")
    assert res.status_code == 403


def test_reversed_dates_rejected(client):
    req = {
        "aoi_id": "predefined-nairobi",
        "start_date": "2024-05-01",
        "end_date": "2024-01-01",
        "indicators": ["ndvi"],
    }
    res = client.post("/api/analysis", json=req)
    assert res.status_code == 422


def test_unsupported_indicator_rejected(client):
    req = {
        "aoi_id": "predefined-nairobi",
        "start_date": "2024-01-01",
        "end_date": "2024-02-01",
        "indicators": ["invalid_indicator"],
    }
    res = client.post("/api/analysis", json=req)
    assert res.status_code == 422
