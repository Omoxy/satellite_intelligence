"""Sentinel Hub Process API live data client.

Authenticates via OAuth2 client credentials (no secrets ever logged),
requests Sentinel-2 L2A multi-band GeoTIFF for an AOI, caches the result
on disk, and returns the local path for consumption by the rasterio engine.

Bands fetched (in order, 1-indexed in the output GeoTIFF):
  1  B02  Blue   ~490 nm
  2  B03  Green  ~560 nm
  3  B04  Red    ~665 nm
  4  B08  NIR    ~842 nm
  5  B11  SWIR-1 ~1610 nm

All reflectance values are normalised to [0, 1] (divide by 10000 from DN).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)

# Sentinel Hub / CDSE OAuth2 token endpoint
# The sh-* client IDs belong to Copernicus Data Space Ecosystem (CDSE)
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

# CDSE Sentinel Hub Process API endpoint
PROCESS_API_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# Directory where fetched GeoTIFFs are cached
RASTER_DIR = Path(config.RASTER_CACHE_DIR)
RASTER_DIR.mkdir(parents=True, exist_ok=True)

# Sentinel-2 L2A evalscript — returns 5 bands as float32 reflectance [0, 1]
EVALSCRIPT = """
//VERSION=3
function setup() {
    return {
        input: [{ bands: ["B02", "B03", "B04", "B08", "B11"], units: "REFLECTANCE" }],
        output: { bands: 5, sampleType: "FLOAT32" }
    };
}
function evaluatePixel(sample) {
    return [sample.B02, sample.B03, sample.B04, sample.B08, sample.B11];
}
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _bbox_from_geom(geom_geojson: dict) -> list[float]:
    """Return [west, south, east, north] from a GeoJSON geometry."""
    from shapely.geometry import shape
    geom = shape(geom_geojson)
    return list(geom.bounds)  # (minx, miny, maxx, maxy)


def _cache_path(bbox: list[float], date_str: str) -> Path:
    """Deterministic cache file name for a given bbox + date."""
    w, s, e, n = [round(v, 4) for v in bbox]
    safe = f"live_{w}_{s}_{e}_{n}_{date_str}.tif".replace("-", "").replace(".", "p")
    return RASTER_DIR / safe


# ---------------------------------------------------------------------------
# OAuth2 token acquisition
# ---------------------------------------------------------------------------

_token_cache: dict = {}


def _get_access_token() -> str:
    """Return a valid OAuth2 bearer token; refresh if expired.

    Credentials are read from config (environment variables) and are
    NEVER written to any log output.
    """
    now = time.time()
    if _token_cache.get("expires_at", 0) > now + 30:
        return _token_cache["access_token"]

    client_id = config.SENTINEL_HUB_CLIENT_ID
    client_secret = config.SENTINEL_HUB_CLIENT_SECRET

    if not client_id or not client_secret:
        raise RuntimeError(
            "Sentinel Hub credentials are not configured. "
            "Set SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET in .env."
        )

    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=20,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Sentinel Hub OAuth2 token request failed: {exc}") from exc

    token_data = resp.json()
    _token_cache["access_token"] = token_data["access_token"]
    _token_cache["expires_at"] = now + int(token_data.get("expires_in", 3600))

    logger.info("Sentinel Hub: OAuth2 token acquired (expires_in=%s s)", token_data.get("expires_in"))
    return _token_cache["access_token"]


# ---------------------------------------------------------------------------
# Process API request
# ---------------------------------------------------------------------------

def _fetch_sentinel2_tif(
    bbox: list[float],
    date_str: str,
    out_path: Path,
) -> None:
    """Call the Sentinel Hub Process API and write the GeoTIFF to out_path."""
    token = _get_access_token()

    west, south, east, north = bbox

    # Clamp date window: request ±5 days around target date for coverage
    from datetime import datetime, timedelta
    target = datetime.strptime(date_str, "%Y-%m-%d")
    date_from = (target - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00Z")
    date_to = (target + timedelta(days=5)).strftime("%Y-%m-%dT23:59:59Z")

    payload = {
        "input": {
            "bounds": {
                "bbox": [west, south, east, north],
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {"from": date_from, "to": date_to},
                        "maxCloudCoverage": 80,
                        "mosaickingOrder": "leastCC",
                    },
                }
            ],
        },
        "output": {
            "width": 256,
            "height": 256,
            "responses": [
                {
                    "identifier": "default",
                    "format": {"type": "image/tiff", "parameters": {"compression": "LZW"}},
                }
            ],
        },
        "evalscript": EVALSCRIPT,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "image/tiff",
    }

    logger.info(
        "Sentinel Hub Process API: requesting S2-L2A for bbox=[%.4f,%.4f,%.4f,%.4f] date=%s",
        west, south, east, north, date_str,
    )

    try:
        resp = requests.post(
            PROCESS_API_URL,
            json=payload,
            headers=headers,
            timeout=60,
            stream=True,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Sentinel Hub Process API request failed: {exc}") from exc

    content_type = resp.headers.get("Content-Type", "")
    if "tiff" not in content_type and "octet-stream" not in content_type:
        raise RuntimeError(
            f"Sentinel Hub returned unexpected content type: {content_type}. "
            f"Body prefix: {resp.content[:200]!r}"
        )

    out_path.write_bytes(resp.content)
    logger.info("Sentinel Hub: GeoTIFF saved to %s (%d bytes)", out_path.name, len(resp.content))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_live_raster(geom_geojson: dict, date_str: str) -> Optional[Path]:
    """Fetch a live Sentinel-2 L2A GeoTIFF for the AOI and return its path.

    Returns None if credentials are absent or the request fails, so the
    caller can fall back to the deterministic GeoTIFF engine.

    The downloaded file is cached; a second call with the same bbox + date
    returns immediately without a network request.
    """
    if not config.SENTINEL_HUB_CLIENT_ID or not config.SENTINEL_HUB_CLIENT_SECRET:
        logger.warning("Sentinel Hub credentials not configured; skipping live fetch.")
        return None

    bbox = _bbox_from_geom(geom_geojson)
    cached = _cache_path(bbox, date_str)

    if cached.exists() and cached.stat().st_size > 1000:
        logger.info("Sentinel Hub: cache hit for %s", cached.name)
        return cached

    try:
        _fetch_sentinel2_tif(bbox, date_str, cached)
    except RuntimeError as exc:
        logger.error("Sentinel Hub live fetch failed: %s", exc)
        if cached.exists():
            cached.unlink(missing_ok=True)
        return None

    return cached


def test_connection() -> dict:
    """Attempt OAuth2 authentication and return a status dict.

    Never includes the token value or any secret in the returned dict.
    """
    result: dict = {
        "credentials_configured": bool(
            config.SENTINEL_HUB_CLIENT_ID and config.SENTINEL_HUB_CLIENT_SECRET
        ),
        "auth_ok": False,
        "error": None,
    }

    if not result["credentials_configured"]:
        result["error"] = "SENTINEL_HUB_CLIENT_ID or SENTINEL_HUB_CLIENT_SECRET is empty."
        return result

    try:
        _get_access_token()
        result["auth_ok"] = True
    except RuntimeError as exc:
        result["error"] = str(exc)

    return result
