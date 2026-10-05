"""Application configuration loaded from environment variables.

All secrets and credentials are read from the environment at startup.
Nothing is hard-coded. Default values allow demo mode without any .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Absolute path to the backend/ directory
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# --- Server ---
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,https://satelliteintelligence.netlify.app",
    ).split(",")
    if origin.strip()
]
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
API_ACCESS_KEY: str = os.getenv("API_ACCESS_KEY", "")

# --- Database ---
DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(DATA_DIR / "satellite_intelligence.db"))

# --- Data Mode ---
DATA_MODE: str = os.getenv("DATA_MODE", "demo")

# --- Sentinel Hub (only used when DATA_MODE=live) ---
SENTINEL_HUB_CLIENT_ID: str = os.getenv("SENTINEL_HUB_CLIENT_ID", "")
SENTINEL_HUB_CLIENT_SECRET: str = os.getenv("SENTINEL_HUB_CLIENT_SECRET", "")
SENTINEL_HUB_INSTANCE_ID: str = os.getenv("SENTINEL_HUB_INSTANCE_ID", "")

# --- Logging ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# --- Limits ---
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
MAX_AOI_AREA_SQ_KM: float = float(os.getenv("MAX_AOI_AREA_SQ_KM", "10000"))
MAX_REQUEST_SIZE_MB: int = int(os.getenv("MAX_REQUEST_SIZE_MB", "10"))

# Generated rasters and live-data cache can be placed on a persistent disk.
RASTER_CACHE_DIR: Path = Path(os.getenv("RASTER_CACHE_DIR", str(DATA_DIR / "rasters")))

# Minimum AOI area to prevent degenerate geometries (square meters)
MIN_AOI_AREA_SQ_M: float = 1000.0

# Demo raster dimensions (pixels per side)
DEMO_RASTER_SIZE: int = 256


def is_demo_mode() -> bool:
    """Return True when running with deterministic demonstration data."""
    return DATA_MODE == "demo"
