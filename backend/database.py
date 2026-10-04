"""SpatiaLite / SQLite embedded spatial database initialisation and connection management.

This project uses SpatiaLite as an embedded spatial database to keep the portfolio
application self-contained and easy to run locally. SpatiaLite provides geometry
storage, spatial functions, and spatial indexing without requiring a separate
database server. It was selected for portability rather than because it is
interchangeable with PostgreSQL/PostGIS in every operational respect. A production
multi-user deployment could migrate the schema and spatial query patterns to
PostgreSQL/PostGIS, which provides a broader enterprise database ecosystem and
operational capabilities.

Schema stores AOIs, analysis runs, indicator results, time series, change detection
results, and anomalies. Geometry is stored as GeoJSON text with spatial operations
performed via Shapely and spatial indexes.
"""

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import config

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS areas_of_interest (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    geometry      TEXT NOT NULL,          -- GeoJSON Geometry object
    area_sq_km    REAL,
    centroid_lat  REAL,
    centroid_lon  REAL,
    bbox_west     REAL,
    bbox_south    REAL,
    bbox_east     REAL,
    bbox_north    REAL,
    is_predefined INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id               TEXT PRIMARY KEY,
    aoi_id           TEXT NOT NULL REFERENCES areas_of_interest(id),
    start_date       TEXT NOT NULL,        -- ISO-8601 date
    end_date         TEXT NOT NULL,
    indicators       TEXT NOT NULL,        -- JSON array of indicator names
    status           TEXT NOT NULL DEFAULT 'pending',
    data_source      TEXT NOT NULL DEFAULT 'demo',
    cloud_cover_pct  REAL,
    processing_notes TEXT,
    created_at       TEXT NOT NULL,
    completed_at     TEXT
);

CREATE TABLE IF NOT EXISTS indicator_results (
    id            TEXT PRIMARY KEY,
    analysis_id   TEXT NOT NULL REFERENCES analysis_runs(id),
    indicator     TEXT NOT NULL,           -- ndvi | ndmi | ndwi | ndbi
    mean_value    REAL,
    min_value     REAL,
    max_value     REAL,
    std_value     REAL,
    pixel_count   INTEGER,
    nodata_count  INTEGER,
    histogram     TEXT,                    -- JSON: {bins: [...], counts: [...]}
    raster_png    TEXT,                    -- base64-encoded RGBA PNG overlay
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS change_results (
    id               TEXT PRIMARY KEY,
    analysis_id      TEXT NOT NULL REFERENCES analysis_runs(id),
    indicator        TEXT NOT NULL,
    period1_mean     REAL,
    period2_mean     REAL,
    absolute_change  REAL,
    percentage_change REAL,
    increase_pct     REAL,
    decrease_pct     REAL,
    stable_pct       REAL,
    change_raster    TEXT,                 -- base64-encoded change map PNG
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS timeseries (
    id           TEXT PRIMARY KEY,
    analysis_id  TEXT NOT NULL REFERENCES analysis_runs(id),
    indicator    TEXT NOT NULL,
    date         TEXT NOT NULL,
    mean_value   REAL,
    min_value    REAL,
    max_value    REAL,
    data_quality TEXT                       -- good | partial | poor
);

CREATE TABLE IF NOT EXISTS anomalies (
    id              TEXT PRIMARY KEY,
    analysis_id     TEXT NOT NULL REFERENCES analysis_runs(id),
    indicator       TEXT NOT NULL,
    baseline_value  REAL,
    current_value   REAL,
    deviation       REAL,
    threshold       REAL,
    classification  TEXT NOT NULL,          -- normal | watch | warning | alert
    description     TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classification_results (
    id            TEXT PRIMARY KEY,
    analysis_id   TEXT NOT NULL REFERENCES analysis_runs(id),
    class_name    TEXT NOT NULL,
    area_pct      REAL,
    pixel_count   INTEGER,
    created_at    TEXT NOT NULL
);

-- Indexes for query performance (analogous to PostGIS GiST indexes)
CREATE INDEX IF NOT EXISTS idx_analysis_aoi ON analysis_runs(aoi_id);
CREATE INDEX IF NOT EXISTS idx_indicators_analysis ON indicator_results(analysis_id);
CREATE INDEX IF NOT EXISTS idx_change_analysis ON change_results(analysis_id);
CREATE INDEX IF NOT EXISTS idx_timeseries_analysis ON timeseries(analysis_id, indicator);
CREATE INDEX IF NOT EXISTS idx_anomalies_analysis ON anomalies(analysis_id);
CREATE INDEX IF NOT EXISTS idx_classification_analysis ON classification_results(analysis_id);
"""


def _db_path() -> Path:
    """Resolve database file path, creating parent directories."""
    path = Path(config.DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    """Create tables and indexes if they do not exist."""
    path = _db_path()
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        logger.info("Database initialised at %s", path)
    finally:
        conn.close()


@contextmanager
def get_connection():
    """Yield a database connection with row_factory set.

    Usage::

        with get_connection() as conn:
            rows = conn.execute("SELECT ...").fetchall()
    """
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def new_id() -> str:
    """Generate a new UUID-4 primary key."""
    return str(uuid.uuid4())


def utcnow() -> str:
    """ISO-8601 timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()
