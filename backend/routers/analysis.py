"""Earth Observation Analysis Router.

Executes genuine geospatial and remote sensing calculations across
Sentinel-2 spectral bands. Orchestrates spectral indices (NDVI, NDMI,
NDWI, NDBI), zonal statistics, multi-temporal change detection,
statistical anomaly detection, and rule-based land-cover classification.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

import config
import database
from engine import (
    anomaly,
    change_detection,
    classification,
    demo_data,
    geometry,
    raster_engine,
    rendering,
    spectral,
    statistics,
)
from models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnomalyResult,
    AOIResponse,
    ChangeResult,
    ClassificationResult,
    IndicatorStats,
    SuccessResponse,
    TimeseriesPoint,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["Earth Observation Analysis"])


@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def run_analysis(payload: AnalysisRequest):
    """Execute an Earth Observation analysis on an Area of Interest.

    Processing pipeline:
    1. Validate AOI and retrieve geometry from database
    2. Acquire surface reflectance bands for requested observation dates
    3. Calculate spectral indices (NDVI, NDMI, NDWI, NDBI)
    4. Compute zonal statistics & render geo-referenced PNG overlays
    5. Detect spatial and numerical changes between start and end dates
    6. Perform historical baseline anomaly detection
    7. Generate rule-based land-cover classification
    8. Calculate temporal time-series trend
    9. Persist all analytical results and metadata
    """
    # Step 1: Retrieve AOI
    with database.get_connection() as conn:
        aoi_row = conn.execute(
            """
            SELECT id, name, geometry, area_sq_km, centroid_lat, centroid_lon,
                   bbox_west, bbox_south, bbox_east, bbox_north, is_predefined, created_at
            FROM areas_of_interest WHERE id = ?
            """,
            (payload.aoi_id,),
        ).fetchone()

    if not aoi_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Area of Interest with ID '{payload.aoi_id}' not found",
        )

    aoi_geom = json.loads(aoi_row["geometry"])
    analysis_id = database.new_id()
    now = database.utcnow()

    # Step 2: Acquire observation data (start_date, end_date, and baseline history)
    # Using genuine Rasterio multi-band GeoTIFF clipping pipeline
    clipped_end = raster_engine.load_and_clip_raster(aoi_geom, payload.end_date)
    clipped_start = raster_engine.load_and_clip_raster(aoi_geom, payload.start_date)

    bands_end_dict = clipped_end.bands
    bands_start_dict = clipped_start.bands

    # Step 3 & 4: Compute Spectral Indices & Zonal Statistics
    calculated_indices: dict[str, Any] = {}
    indicator_stats_map: dict[str, IndicatorStats] = {}

    for ind in payload.indicators:
        arr_end = spectral.calculate_index(ind, bands_end_dict)
        calculated_indices[ind] = arr_end
        stats = statistics.compute_statistics(arr_end)
        png_overlay = rendering.render_to_png_base64(arr_end, ind, alpha=190)

        indicator_stats_map[ind] = IndicatorStats(
            indicator=ind,
            mean=stats["mean"],
            min=stats["min"],
            max=stats["max"],
            std=stats["std"],
            pixel_count=stats["pixel_count"],
            nodata_count=stats["nodata_count"],
            histogram=stats["histogram"],
            raster_overlay=png_overlay,
        )

    # Step 5: Multi-temporal Change Detection (between start_date and end_date)
    change_results_list: list[ChangeResult] = []
    # Primary change calculation on NDVI (or first available indicator)
    primary_change_ind = "ndvi" if "ndvi" in payload.indicators else payload.indicators[0]
    arr_start_primary = spectral.calculate_index(primary_change_ind, bands_start_dict)
    arr_end_primary = calculated_indices[primary_change_ind]

    chg = change_detection.compute_change(arr_start_primary, arr_end_primary)
    chg_overlay = rendering.render_to_png_base64(chg["absolute_change"], "change", alpha=190)

    chg_model = ChangeResult(
        indicator=primary_change_ind,
        period1_mean=chg["period1_mean"],
        period2_mean=chg["period2_mean"],
        absolute_change=chg["abs_change_mean"],
        percentage_change=chg["pct_change_mean"],
        increase_pct=chg["increase_pct"],
        decrease_pct=chg["decrease_pct"],
        stable_pct=chg["stable_pct"],
        change_overlay=chg_overlay,
    )
    change_results_list.append(chg_model)

    # Step 6: Historical Baseline Anomaly Detection
    # Acquire historical baseline observations from GeoTIFF rasters clipped to this AOI
    historical_dates = ["2023-04-15", "2023-08-15", "2023-11-15", "2024-01-01"]
    baseline_observations: list[Any] = []
    for h_date in historical_dates:
        h_clipped = raster_engine.load_and_clip_raster(aoi_geom, h_date)
        h_idx = spectral.calculate_index(primary_change_ind, h_clipped.bands)
        baseline_observations.append(h_idx)

    baseline = anomaly.compute_baseline(baseline_observations)
    anom = anomaly.detect_anomalies(
        arr_end_primary,
        baseline["mean"],
        baseline["std"],
        primary_change_ind,
    )

    anomalies_list: list[AnomalyResult] = [
        AnomalyResult(
            indicator=primary_change_ind,
            baseline_value=anom["baseline_value"],
            current_value=anom["current_value"],
            deviation=anom["deviation_value"],
            threshold=anom["threshold"],
            classification=anom["classification"],
            description=anom["description"],
        )
    ]

    # Step 7: Rule-based Land-cover Classification
    # Compute all required indices for classification if not already calculated
    ndvi_for_lc = calculated_indices.get("ndvi", spectral.calculate_index("ndvi", bands_end_dict))
    ndwi_for_lc = calculated_indices.get("ndwi", spectral.calculate_index("ndwi", bands_end_dict))
    ndbi_for_lc = calculated_indices.get("ndbi", spectral.calculate_index("ndbi", bands_end_dict))

    lc = classification.classify_land_cover(ndvi_for_lc, ndwi_for_lc, ndbi_for_lc)
    classification_list: list[ClassificationResult] = [
        ClassificationResult(
            class_name=c["class_name"],
            area_pct=c["area_pct"],
            pixel_count=c["pixel_count"],
        )
        for c in lc["class_areas"]
    ]

    # Step 8: Multi-temporal Time-Series
    # Load observations from multi-temporal GeoTIFF rasters clipped to this AOI
    timeseries_dict: dict[str, list[TimeseriesPoint]] = {}
    ts_dates = ["2023-04-15", "2023-08-15", "2023-11-15", "2024-01-01", "2024-03-15"]
    # Ensure start_date and end_date are represented if distinct
    for custom_d in [payload.start_date, payload.end_date]:
        if custom_d not in ts_dates:
            ts_dates.append(custom_d)
    ts_dates = sorted(ts_dates)

    # Pre-load clipped observations for all dates
    clipped_series = {d: raster_engine.load_and_clip_raster(aoi_geom, d) for d in ts_dates}

    for ind in payload.indicators:
        ts_points: list[TimeseriesPoint] = []
        for obs_date in ts_dates:
            b_sample = clipped_series[obs_date]
            idx_sample = spectral.calculate_index(ind, b_sample.bands)
            sample_stats = statistics.compute_statistics(idx_sample)
            quality_flag = "good" if b_sample.cloud_cover_pct < 10 else ("partial" if b_sample.cloud_cover_pct < 20 else "poor")
            ts_points.append(
                TimeseriesPoint(
                    date=obs_date,
                    mean=sample_stats["mean"],
                    min=sample_stats["min"],
                    max=sample_stats["max"],
                    data_quality=quality_flag,
                )
            )
        timeseries_dict[ind] = ts_points

    # Determine whether live or synthetic data was used
    is_live_data = clipped_end.source_file.startswith("live_")
    data_source_label = (
        f"Live Sentinel-2 L2A CDSE ({clipped_end.source_file})"
        if is_live_data
        else f"Deterministic GeoTIFF Rasterio Pipeline ({clipped_end.source_file})"
    )

    # Synthesis & Summary
    summary = {
        "study_area_name": aoi_row["name"],
        "area_sq_km": aoi_row["area_sq_km"],
        "analysis_period": f"{payload.start_date} to {payload.end_date}",
        "data_source": data_source_label,
        "cloud_cover_pct": clipped_end.cloud_cover_pct,
        "primary_vegetation_status": "Vigorous / Healthy" if (indicator_stats_map.get("ndvi") and indicator_stats_map["ndvi"].mean and indicator_stats_map["ndvi"].mean > 0.4) else "Sparse / Moderate",
        "change_trend": "Increasing" if (chg["abs_change_mean"] and chg["abs_change_mean"] > 0.02) else ("Decreasing" if (chg["abs_change_mean"] and chg["abs_change_mean"] < -0.02) else "Stable"),
        "vegetation_anomaly_status": anom["classification"].upper(),
        "limitations": [
            "Optical imagery is sensitive to cloud contamination and atmospheric aerosol variations."
            if is_live_data
            else "Demonstration Mode: band reflectance is derived from deterministic physically-constrained synthesis.",
            "Remotely-sensed indices are proxies for surface biogeophysical properties and do not substitute for on-the-ground agronomic verification.",
        ],
    }

    # Step 9: Database Persistence
    with database.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_runs (
                id, aoi_id, start_date, end_date, indicators, status,
                data_source, cloud_cover_pct, processing_notes, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, 'completed', 'demo', ?, ?, ?, ?)
            """,
            (
                analysis_id,
                payload.aoi_id,
                payload.start_date,
                payload.end_date,
                json.dumps(payload.indicators),
                clipped_end.cloud_cover_pct,
                f"Computed across {len(payload.indicators)} indices with {len(ts_dates)} temporal steps.",
                now,
                database.utcnow(),
            ),
        )

        # Store Indicator Results
        for ind_name, stat_item in indicator_stats_map.items():
            conn.execute(
                """
                INSERT INTO indicator_results (
                    id, analysis_id, indicator, mean_value, min_value, max_value,
                    std_value, pixel_count, nodata_count, histogram, raster_png, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    database.new_id(),
                    analysis_id,
                    ind_name,
                    stat_item.mean,
                    stat_item.min,
                    stat_item.max,
                    stat_item.std,
                    stat_item.pixel_count,
                    stat_item.nodata_count,
                    json.dumps(stat_item.histogram),
                    stat_item.raster_overlay,
                    now,
                ),
            )

        # Store Change Results
        for chg_item in change_results_list:
            conn.execute(
                """
                INSERT INTO change_results (
                    id, analysis_id, indicator, period1_mean, period2_mean,
                    absolute_change, percentage_change, increase_pct, decrease_pct,
                    stable_pct, change_raster, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    database.new_id(),
                    analysis_id,
                    chg_item.indicator,
                    chg_item.period1_mean,
                    chg_item.period2_mean,
                    chg_item.absolute_change,
                    chg_item.percentage_change,
                    chg_item.increase_pct,
                    chg_item.decrease_pct,
                    chg_item.stable_pct,
                    chg_item.change_overlay,
                    now,
                ),
            )

        # Store Timeseries
        for ind_name, pts in timeseries_dict.items():
            for p in pts:
                conn.execute(
                    """
                    INSERT INTO timeseries (
                        id, analysis_id, indicator, date, mean_value, min_value, max_value, data_quality
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        database.new_id(),
                        analysis_id,
                        ind_name,
                        p.date,
                        p.mean,
                        p.min,
                        p.max,
                        p.data_quality,
                    ),
                )

        # Store Anomalies
        for anom_item in anomalies_list:
            conn.execute(
                """
                INSERT INTO anomalies (
                    id, analysis_id, indicator, baseline_value, current_value,
                    deviation, threshold, classification, description, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    database.new_id(),
                    analysis_id,
                    anom_item.indicator,
                    anom_item.baseline_value,
                    anom_item.current_value,
                    anom_item.deviation,
                    anom_item.threshold,
                    anom_item.classification,
                    anom_item.description,
                    now,
                ),
            )

        # Store Classification
        for lc_item in classification_list:
            conn.execute(
                """
                INSERT INTO classification_results (
                    id, analysis_id, class_name, area_pct, pixel_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    database.new_id(),
                    analysis_id,
                    lc_item.class_name,
                    lc_item.area_pct,
                    lc_item.pixel_count,
                    now,
                ),
            )

    aoi_resp = AOIResponse(
        id=aoi_row["id"],
        name=aoi_row["name"],
        geometry=aoi_geom,
        area_sq_km=aoi_row["area_sq_km"],
        centroid={"lat": aoi_row["centroid_lat"], "lng": aoi_row["centroid_lon"]},
        bbox={
            "west": aoi_row["bbox_west"],
            "south": aoi_row["bbox_south"],
            "east": aoi_row["bbox_east"],
            "north": aoi_row["bbox_north"],
        },
        is_predefined=bool(aoi_row["is_predefined"]),
        created_at=aoi_row["created_at"],
    )

    response_data = AnalysisResponse(
        id=analysis_id,
        aoi_id=payload.aoi_id,
        aoi=aoi_resp,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="completed",
        data_source=data_source_label,
        cloud_cover_pct=clipped_end.cloud_cover_pct,
        processing_notes=f"Generated {len(payload.indicators)} indices and multi-temporal metrics.",
        indicators=indicator_stats_map,
        change_detection=change_results_list,
        timeseries=timeseries_dict,
        anomalies=anomalies_list,
        classification=classification_list,
        summary=summary,
        created_at=now,
        completed_at=database.utcnow(),
    )

    return SuccessResponse(data={"analysis": response_data.model_dump()})


@router.get("/{analysis_id}", response_model=SuccessResponse)
def get_analysis(analysis_id: str):
    """Retrieve full analysis report and overlays by analysis ID."""
    with database.get_connection() as conn:
        run = conn.execute(
            "SELECT * FROM analysis_runs WHERE id = ?",
            (analysis_id,),
        ).fetchone()

        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")

        aoi_row = conn.execute(
            "SELECT * FROM areas_of_interest WHERE id = ?",
            (run["aoi_id"],),
        ).fetchone()

        # Indicator results
        ind_rows = conn.execute(
            "SELECT * FROM indicator_results WHERE analysis_id = ?",
            (analysis_id,),
        ).fetchall()
        indicators: dict[str, IndicatorStats] = {}
        for ir in ind_rows:
            indicators[ir["indicator"]] = IndicatorStats(
                indicator=ir["indicator"],
                mean=ir["mean_value"],
                min=ir["min_value"],
                max=ir["max_value"],
                std=ir["std_value"],
                pixel_count=ir["pixel_count"],
                nodata_count=ir["nodata_count"],
                histogram=json.loads(ir["histogram"]) if ir["histogram"] else None,
                raster_overlay=ir["raster_png"],
            )

        # Change results
        chg_rows = conn.execute(
            "SELECT * FROM change_results WHERE analysis_id = ?",
            (analysis_id,),
        ).fetchall()
        change_results: list[ChangeResult] = [
            ChangeResult(
                indicator=cr["indicator"],
                period1_mean=cr["period1_mean"],
                period2_mean=cr["period2_mean"],
                absolute_change=cr["absolute_change"],
                percentage_change=cr["percentage_change"],
                increase_pct=cr["increase_pct"],
                decrease_pct=cr["decrease_pct"],
                stable_pct=cr["stable_pct"],
                change_overlay=cr["change_raster"],
            )
            for cr in chg_rows
        ]

        # Timeseries
        ts_rows = conn.execute(
            "SELECT * FROM timeseries WHERE analysis_id = ? ORDER BY date ASC",
            (analysis_id,),
        ).fetchall()
        timeseries: dict[str, list[TimeseriesPoint]] = {}
        for tr in ts_rows:
            ind = tr["indicator"]
            if ind not in timeseries:
                timeseries[ind] = []
            timeseries[ind].append(
                TimeseriesPoint(
                    date=tr["date"],
                    mean=tr["mean_value"],
                    min=tr["min_value"],
                    max=tr["max_value"],
                    data_quality=tr["data_quality"],
                )
            )

        # Anomalies
        anom_rows = conn.execute(
            "SELECT * FROM anomalies WHERE analysis_id = ?",
            (analysis_id,),
        ).fetchall()
        anomalies: list[AnomalyResult] = [
            AnomalyResult(
                indicator=ar["indicator"],
                baseline_value=ar["baseline_value"],
                current_value=ar["current_value"],
                deviation=ar["deviation"],
                threshold=ar["threshold"],
                classification=ar["classification"],
                description=ar["description"],
            )
            for ar in anom_rows
        ]

        # Classification
        cl_rows = conn.execute(
            "SELECT * FROM classification_results WHERE analysis_id = ?",
            (analysis_id,),
        ).fetchall()
        classification_results: list[ClassificationResult] = [
            ClassificationResult(
                class_name=clr["class_name"],
                area_pct=clr["area_pct"],
                pixel_count=clr["pixel_count"],
            )
            for clr in cl_rows
        ]

    aoi_data = None
    if aoi_row:
        aoi_data = AOIResponse(
            id=aoi_row["id"],
            name=aoi_row["name"],
            geometry=json.loads(aoi_row["geometry"]),
            area_sq_km=aoi_row["area_sq_km"],
            centroid={"lat": aoi_row["centroid_lat"], "lng": aoi_row["centroid_lon"]},
            bbox={
                "west": aoi_row["bbox_west"],
                "south": aoi_row["bbox_south"],
                "east": aoi_row["bbox_east"],
                "north": aoi_row["bbox_north"],
            },
            is_predefined=bool(aoi_row["is_predefined"]),
            created_at=aoi_row["created_at"],
        )

    res = AnalysisResponse(
        id=run["id"],
        aoi_id=run["aoi_id"],
        aoi=aoi_data,
        start_date=run["start_date"],
        end_date=run["end_date"],
        status=run["status"],
        data_source=run["data_source"],
        cloud_cover_pct=run["cloud_cover_pct"],
        processing_notes=run["processing_notes"],
        indicators=indicators,
        change_detection=change_results,
        timeseries=timeseries,
        anomalies=anomalies,
        classification=classification_results,
        created_at=run["created_at"],
        completed_at=run["completed_at"],
    )

    return SuccessResponse(data={"analysis": res.model_dump()})
