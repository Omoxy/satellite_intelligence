"""Security and input validation tests."""

import hashlib
import hmac
import secrets
import time

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import config
import database
from main import app
from security import client_identifier, rate_limiter


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


def test_write_operations_require_api_key_in_production(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    api_access_key = secrets.token_urlsafe(32)
    monkeypatch.setattr(config, "API_ACCESS_KEY", api_access_key)
    rate_limiter.reset()
    payload = {
        "name": "Protected AOI",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[36.8, -1.3], [36.9, -1.3], [36.9, -1.2], [36.8, -1.2], [36.8, -1.3]]],
        },
    }

    with TestClient(app) as protected_client:
        assert protected_client.post("/api/areas", json=payload).status_code == 401
        create_response = protected_client.post(
            "/api/areas", json=payload, headers={"X-API-Key": api_access_key}
        )
        assert create_response.status_code == 201
        area_id = create_response.json()["data"]["area"]["id"]
        assert protected_client.delete(f"/api/areas/{area_id}").status_code == 401
        assert protected_client.delete(
            f"/api/areas/{area_id}", headers={"X-API-Key": config.API_ACCESS_KEY}
        ).status_code == 200
        assert protected_client.post("/api/analysis", json={}).status_code == 401


def test_fake_client_credentials_cannot_authorize_protected_writes(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "API_ACCESS_KEY", secrets.token_urlsafe(32))
    rate_limiter.reset()
    fake_credentials = {
        "X-API-Key": "not-the-server-key",
        "Authorization": f"Bearer {config.API_ACCESS_KEY}",
        "X-Proxy-Client-IP": "203.0.113.8",
        "X-Proxy-Timestamp": str(int(time.time())),
        "X-Proxy-Signature": "client-cannot-sign-this",
    }
    area_payload = {
        "name": "Unauthenticated AOI",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[36.8, -1.3], [36.9, -1.3], [36.9, -1.2], [36.8, -1.2], [36.8, -1.3]]],
        },
    }
    analysis_payload = {
        "aoi_id": "predefined-nairobi",
        "start_date": "2024-01-01",
        "end_date": "2024-02-01",
        "indicators": ["ndvi"],
    }

    with TestClient(app) as protected_client:
        assert protected_client.post(
            "/api/areas", json=area_payload, headers=fake_credentials
        ).status_code == 401
        assert protected_client.delete(
            "/api/areas/custom-area", headers=fake_credentials
        ).status_code == 401
        assert protected_client.post(
            "/api/analysis", json=analysis_payload, headers=fake_credentials
        ).status_code == 401


def test_health_and_public_get_remain_accessible_in_production(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "API_ACCESS_KEY", secrets.token_urlsafe(32))
    rate_limiter.reset()

    with TestClient(app) as protected_client:
        assert protected_client.get("/health").status_code == 200
        assert protected_client.get("/api/areas").status_code == 200


def test_production_startup_requires_api_key(monkeypatch):
    monkeypatch.setattr(config, "ENVIRONMENT", "production")
    monkeypatch.setattr(config, "API_ACCESS_KEY", "")

    with pytest.raises(RuntimeError, match="API_ACCESS_KEY"):
        with TestClient(app):
            pass


def test_analysis_has_stricter_rate_limit(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MINUTE", 5)
    rate_limiter.reset()

    with TestClient(app) as limited_client:
        assert limited_client.post("/api/analysis", json={}).status_code == 422
        assert limited_client.post("/api/analysis", json={}).status_code == 429


def test_proxy_client_ip_requires_valid_signature(monkeypatch):
    api_access_key = secrets.token_urlsafe(32)
    monkeypatch.setattr(config, "API_ACCESS_KEY", api_access_key)
    client_ip = "203.0.113.8"
    timestamp = str(int(time.time()))
    signature = hmac.new(
        api_access_key.encode(), f"{timestamp}:{client_ip}".encode(), hashlib.sha256
    ).hexdigest()
    headers = [
        (b"x-proxy-client-ip", client_ip.encode()),
        (b"x-proxy-timestamp", timestamp.encode()),
        (b"x-proxy-signature", signature.encode()),
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/areas",
        "headers": headers,
        "client": ("127.0.0.1", 1234),
    }

    assert client_identifier(Request(scope)) == client_ip
    scope["headers"] = headers[:-1] + [(b"x-proxy-signature", b"invalid")]
    assert client_identifier(Request(scope)) == "127.0.0.1"


def test_oversized_request_body_is_rejected(monkeypatch):
    monkeypatch.setattr(config, "MAX_REQUEST_SIZE_MB", 0)

    with TestClient(app) as limited_client:
        response = limited_client.post("/api/areas", json={"name": "too large"})
        assert response.status_code == 413
