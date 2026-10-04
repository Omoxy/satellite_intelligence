"""Location Inspector Router.

Provides point-based pixel probing for any coordinate (latitude, longitude).
Calculates real-time spectral indices at the probed point, compares with
baseline historical conditions, and produces a scientifically defensible
interpretation of ground conditions without asserting unverified ground truth.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query, status
from shapely.geometry import Point, shape

import config
import database
from engine import anomaly, raster_engine, spectral
from models.schemas import LocationResponse, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/location", tags=["Location Inspector"])


@router.get("", response_model=SuccessResponse)
def inspect_location(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude in WGS84 decimal degrees"),
    lng: float = Query(..., ge=-180.0, le=180.0, description="Longitude in WGS84 decimal degrees"),
    analysis_id: Optional[str] = Query(None, description="Optional active analysis run ID to contextualise"),
):
    """Probe an exact geographic coordinate for satellite-derived spectral indicators."""
    ref_date = "2024-03-15"

    with database.get_connection() as conn:
        if analysis_id:
            run = conn.execute(
                "SELECT end_date FROM analysis_runs WHERE id = ?",
                (analysis_id,),
            ).fetchone()
            if run and run["end_date"]:
                ref_date = run["end_date"]

    # Sample physical spectral bands directly from GeoTIFF raster using Rasterio
    sampled = raster_engine.sample_point_from_raster(lng, lat, ref_date)

    if not sampled:
        # Fallback to nearest date if requested date had no data at point
        sampled = raster_engine.sample_point_from_raster(lng, lat, "2024-01-01")

    if not sampled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No raster pixel data found for coordinate ({lat:.4f}, {lng:.4f})",
        )

    b_dict = {
        "red": np.array([[sampled["red"]]], dtype=np.float32),
        "green": np.array([[sampled["green"]]], dtype=np.float32),
        "nir": np.array([[sampled["nir"]]], dtype=np.float32),
        "swir": np.array([[sampled["swir"]]], dtype=np.float32),
    }

    ndvi_val = float(spectral.calculate_index("ndvi", b_dict)[0, 0])
    ndmi_val = float(spectral.calculate_index("ndmi", b_dict)[0, 0])
    ndwi_val = float(spectral.calculate_index("ndwi", b_dict)[0, 0])
    ndbi_val = float(spectral.calculate_index("ndbi", b_dict)[0, 0])

    def clean_val(v: float) -> Optional[float]:
        return None if np.isnan(v) else round(v, 4)

    c_ndvi = clean_val(ndvi_val)
    c_ndmi = clean_val(ndmi_val)
    c_ndwi = clean_val(ndwi_val)
    c_ndbi = clean_val(ndbi_val)

    # Historical baseline probe at this exact pixel coordinate from historical GeoTIFF rasters
    baseline_observations: list[float] = []
    hist_dates = ["2023-04-15", "2023-08-15", "2023-11-15", "2024-01-01"]
    for hd in hist_dates:
        h_s = raster_engine.sample_point_from_raster(lng, lat, hd)
        if h_s:
            h_b_dict = {
                "red": np.array([[h_s["red"]]], dtype=np.float32),
                "green": np.array([[h_s["green"]]], dtype=np.float32),
                "nir": np.array([[h_s["nir"]]], dtype=np.float32),
                "swir": np.array([[h_s["swir"]]], dtype=np.float32),
            }
            h_val = float(spectral.calculate_index("ndvi", h_b_dict)[0, 0])
            if not np.isnan(h_val):
                baseline_observations.append(h_val)

    hist_mean = float(np.mean(baseline_observations)) if baseline_observations else 0.45
    hist_std = float(np.std(baseline_observations)) if baseline_observations else 0.08
    hist_std = max(hist_std, 0.02)

    diff = (c_ndvi - hist_mean) if c_ndvi is not None else 0.0
    z_score = diff / hist_std

    if abs(z_score) >= anomaly.SIGMA_ALERT:
        anomaly_status = "ALERT"
    elif abs(z_score) >= anomaly.SIGMA_WARNING:
        anomaly_status = "WARNING"
    elif abs(z_score) >= anomaly.SIGMA_WATCH:
        anomaly_status = "WATCH"
    else:
        anomaly_status = "NORMAL"

    # Contextual Interpretation based strictly on physical indices
    interpretation_parts = []
    if c_ndvi is not None:
        if c_ndvi > 0.6:
            interpretation_parts.append("Dense photosynthetically active canopy.")
        elif c_ndvi > 0.35:
            interpretation_parts.append("Moderate vegetation cover (cropland/grassland).")
        elif c_ndvi > 0.15:
            interpretation_parts.append("Sparse vegetation or dry herbaceous cover.")
        elif c_ndvi >= 0:
            interpretation_parts.append("Bare soil or rock surface.")
        else:
            interpretation_parts.append("Negative NDVI characteristic of water or cloud artifact.")

    if c_ndmi is not None:
        if c_ndmi > 0.2:
            interpretation_parts.append("High canopy/soil moisture detected.")
        elif c_ndmi < -0.1:
            interpretation_parts.append("Elevated moisture stress.")

    if c_ndbi is not None and c_ndbi > 0.08:
        interpretation_parts.append("Impervious surface spectral response indicating built structures or bare compacted soil.")

    interpretation = " ".join(interpretation_parts)
    if not interpretation:
        interpretation = "Point inspection indicates non-vegetated or obscured surface."

    res = LocationResponse(
        lat=round(lat, 6),
        lng=round(lng, 6),
        indicators={
            "ndvi": c_ndvi,
            "ndmi": c_ndmi,
            "ndwi": c_ndwi,
            "ndbi": c_ndbi,
        },
        historical_comparison={
            "baseline_mean_ndvi": round(hist_mean, 4),
            "current_ndvi": c_ndvi,
            "z_score": round(z_score, 2),
            "historical_samples_count": len(baseline_observations),
        },
        anomaly_status=anomaly_status,
        interpretation=interpretation,
    )

    return SuccessResponse(data={"location": res.model_dump()})
