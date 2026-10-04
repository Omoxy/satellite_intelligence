"""Pydantic request and response models.

Strict validation for all API inputs. Response models ensure no
internal state leaks to the client.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AOICreate(BaseModel):
    """Create a new Area of Interest."""

    name: str = Field(..., min_length=1, max_length=200)
    geometry: dict = Field(..., description="GeoJSON Geometry object (Polygon or MultiPolygon)")

    @field_validator("geometry")
    @classmethod
    def validate_geojson_type(cls, v: dict) -> dict:
        geo_type = v.get("type")
        if geo_type not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"Geometry type must be Polygon or MultiPolygon, got '{geo_type}'")
        coords = v.get("coordinates")
        if not coords:
            raise ValueError("Geometry coordinates are required")
        return v


class AnalysisRequest(BaseModel):
    """Request a new analysis run."""

    aoi_id: str = Field(..., min_length=1)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    indicators: list[str] = Field(
        default=["ndvi", "ndmi", "ndwi", "ndbi"],
        min_length=1,
    )

    @field_validator("indicators")
    @classmethod
    def validate_indicators(cls, v: list[str]) -> list[str]:
        allowed = {"ndvi", "ndmi", "ndwi", "ndbi"}
        for ind in v:
            if ind not in allowed:
                raise ValueError(f"Unknown indicator '{ind}'. Allowed: {sorted(allowed)}")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_date_order(cls, v: str, info) -> str:
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must not precede start_date")
        return v


class LocationQuery(BaseModel):
    """Query parameters for the location inspector."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    analysis_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class AOIResponse(BaseModel):
    id: str
    name: str
    geometry: dict
    area_sq_km: Optional[float] = None
    centroid: Optional[dict] = None
    bbox: Optional[dict] = None
    is_predefined: bool = False
    created_at: str


class IndicatorStats(BaseModel):
    indicator: str
    mean: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    std: Optional[float] = None
    pixel_count: Optional[int] = None
    nodata_count: Optional[int] = None
    histogram: Optional[dict] = None
    raster_overlay: Optional[str] = None  # base64 PNG data URL


class ChangeResult(BaseModel):
    indicator: str
    period1_mean: Optional[float] = None
    period2_mean: Optional[float] = None
    absolute_change: Optional[float] = None
    percentage_change: Optional[float] = None
    increase_pct: Optional[float] = None
    decrease_pct: Optional[float] = None
    stable_pct: Optional[float] = None
    change_overlay: Optional[str] = None  # base64 PNG data URL


class TimeseriesPoint(BaseModel):
    date: str
    mean: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    data_quality: str = "good"


class AnomalyResult(BaseModel):
    indicator: str
    baseline_value: Optional[float] = None
    current_value: Optional[float] = None
    deviation: Optional[float] = None
    threshold: Optional[float] = None
    classification: str  # normal | watch | warning | alert
    description: str


class ClassificationResult(BaseModel):
    class_name: str
    area_pct: Optional[float] = None
    pixel_count: Optional[int] = None


class AnalysisResponse(BaseModel):
    id: str
    aoi_id: str
    aoi: Optional[AOIResponse] = None
    start_date: str
    end_date: str
    status: str
    data_source: str
    cloud_cover_pct: Optional[float] = None
    processing_notes: Optional[str] = None
    indicators: dict[str, IndicatorStats] = {}
    change_detection: list[ChangeResult] = []
    timeseries: dict[str, list[TimeseriesPoint]] = {}
    anomalies: list[AnomalyResult] = []
    classification: list[ClassificationResult] = []
    summary: Optional[dict] = None
    created_at: str
    completed_at: Optional[str] = None


class LocationResponse(BaseModel):
    lat: float
    lng: float
    indicators: dict[str, Optional[float]] = {}
    historical_comparison: Optional[dict] = None
    anomaly_status: Optional[str] = None
    interpretation: str = ""


class ErrorResponse(BaseModel):
    status: str = "error"
    error: dict = Field(default_factory=dict)


class SuccessResponse(BaseModel):
    status: str = "success"
    data: dict | list | None = None
    metadata: Optional[dict] = None
