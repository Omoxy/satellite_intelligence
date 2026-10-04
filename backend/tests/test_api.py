"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

import database
from main import app


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    database.init_db()
    from routers.areas import seed_predefined_areas_if_needed
    seed_predefined_areas_if_needed()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_list_areas(client):
    res = client.get("/api/areas")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    areas = data["data"]["areas"]
    assert len(areas) >= 5  # Predefined Kenyan locations


def test_create_and_delete_custom_area(client):
    payload = {
        "name": "Test Farm AOI",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [36.80, -1.30],
                    [36.85, -1.30],
                    [36.85, -1.25],
                    [36.80, -1.25],
                    [36.80, -1.30],
                ]
            ],
        },
    }
    create_res = client.post("/api/areas", json=payload)
    assert create_res.status_code == 201
    area = create_res.json()["data"]["area"]
    area_id = area["id"]
    assert area["name"] == "Test Farm AOI"

    # Delete custom area
    del_res = client.delete(f"/api/areas/{area_id}")
    assert del_res.status_code == 200


def test_full_analysis_workflow(client):
    # 1. Get an area ID (Nairobi)
    areas_res = client.get("/api/areas")
    areas = areas_res.json()["data"]["areas"]
    nairobi = next(a for a in areas if a["name"] == "Nairobi")

    # 2. Trigger analysis
    req = {
        "aoi_id": nairobi["id"],
        "start_date": "2024-01-01",
        "end_date": "2024-03-15",
        "indicators": ["ndvi", "ndmi", "ndwi", "ndbi"],
    }
    an_res = client.post("/api/analysis", json=req)
    assert an_res.status_code == 201
    analysis_data = an_res.json()["data"]["analysis"]
    analysis_id = analysis_data["id"]

    assert "ndvi" in analysis_data["indicators"]
    assert analysis_data["indicators"]["ndvi"]["raster_overlay"] is not None
    assert len(analysis_data["change_detection"]) > 0
    assert len(analysis_data["anomalies"]) > 0
    assert len(analysis_data["classification"]) > 0

    # 3. Retrieve analysis by ID
    get_res = client.get(f"/api/analysis/{analysis_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["analysis"]["id"] == analysis_id


def test_location_inspector(client):
    res = client.get("/api/location?lat=-1.286389&lng=36.817223")
    assert res.status_code == 200
    loc = res.json()["data"]["location"]
    assert "ndvi" in loc["indicators"]
    assert loc["anomaly_status"] in ["NORMAL", "WATCH", "WARNING", "ALERT"]
    assert len(loc["interpretation"]) > 0
