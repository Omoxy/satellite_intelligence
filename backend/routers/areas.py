"""Area of Interest (AOI) router.

Provides endpoints for listing, creating, and retrieving Areas of Interest.
Predefined study areas in Kenya (Nairobi, Nakuru, Murang'a, Siaya,
Elgeyo-Marakwet) are automatically seeded from data/study_areas.json.
Geometry inputs are strictly validated per OGC standards before persistence.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

import config
import database
from engine import geometry
from models.schemas import AOICreate, AOIResponse, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/areas", tags=["Areas of Interest"])


def seed_predefined_areas_if_needed() -> None:
    """Seed the 5 predefined Kenyan study areas if not present."""
    study_areas_file = Path(config.BASE_DIR) / "data" / "study_areas.json"
    if not study_areas_file.exists():
        logger.warning("Study areas file not found at %s", study_areas_file)
        return

    with database.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM areas_of_interest WHERE is_predefined = 1").fetchone()[0]
        if count > 0:
            return  # Already seeded

        try:
            with open(study_areas_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for feat in data.get("features", []):
                props = feat.get("properties", {})
                name = props.get("name", "Study Area")
                geom = feat.get("geometry", {})

                try:
                    valid_geom = geometry.validate_geometry(geom)
                    area_km2 = geometry.compute_area_sq_km(geometry.shape(valid_geom))
                    centroid = geometry.compute_centroid(valid_geom)
                    bbox = geometry.compute_bbox(valid_geom)
                    clean_name = name.lower().replace(" ", "-").replace("'", "")
                    aoi_id = f"predefined-{clean_name}"

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO areas_of_interest (
                            id, name, geometry, area_sq_km, centroid_lat, centroid_lon,
                            bbox_west, bbox_south, bbox_east, bbox_north, is_predefined, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                        """,
                        (
                            aoi_id,
                            name,
                            json.dumps(valid_geom),
                            round(area_km2, 2),
                            centroid["lat"],
                            centroid["lng"],
                            bbox["west"],
                            bbox["south"],
                            bbox["east"],
                            bbox["north"],
                            database.utcnow(),
                        ),
                    )
                except Exception as err:
                    logger.error("Failed to seed area %s: %s", name, err)
        except Exception as e:
            logger.error("Error reading study areas JSON: %s", e)


@router.get("", response_model=SuccessResponse)
def list_areas():
    """List all available Areas of Interest (both predefined and custom)."""
    with database.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, geometry, area_sq_km, centroid_lat, centroid_lon,
                   bbox_west, bbox_south, bbox_east, bbox_north, is_predefined, created_at
            FROM areas_of_interest
            ORDER BY is_predefined DESC, created_at DESC
            """
        ).fetchall()

        areas = []
        for r in rows:
            areas.append(
                AOIResponse(
                    id=r["id"],
                    name=r["name"],
                    geometry=json.loads(r["geometry"]),
                    area_sq_km=r["area_sq_km"],
                    centroid={"lat": r["centroid_lat"], "lng": r["centroid_lon"]},
                    bbox={
                        "west": r["bbox_west"],
                        "south": r["bbox_south"],
                        "east": r["bbox_east"],
                        "north": r["bbox_north"],
                    },
                    is_predefined=bool(r["is_predefined"]),
                    created_at=r["created_at"],
                ).model_dump()
            )

    return SuccessResponse(data={"areas": areas})


@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_area(payload: AOICreate):
    """Create and validate a new custom Area of Interest.

    Validates:
    - GeoJSON format and coordinate hierarchy
    - Non-self-intersection and OGC topology
    - Bounded area size (minimum 1,000 m², maximum 10,000 km²)
    """
    try:
        valid_geom = geometry.validate_geometry(payload.geometry)
    except geometry.GeometryError as ge:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ge))

    geom_shape = geometry.shape(valid_geom)
    area_km2 = geometry.compute_area_sq_km(geom_shape)
    centroid = geometry.compute_centroid(valid_geom)
    bbox = geometry.compute_bbox(valid_geom)
    aoi_id = database.new_id()
    now = database.utcnow()

    with database.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO areas_of_interest (
                id, name, geometry, area_sq_km, centroid_lat, centroid_lon,
                bbox_west, bbox_south, bbox_east, bbox_north, is_predefined, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                aoi_id,
                payload.name.strip(),
                json.dumps(valid_geom),
                round(area_km2, 2),
                centroid["lat"],
                centroid["lng"],
                bbox["west"],
                bbox["south"],
                bbox["east"],
                bbox["north"],
                now,
            ),
        )

    res = AOIResponse(
        id=aoi_id,
        name=payload.name.strip(),
        geometry=valid_geom,
        area_sq_km=round(area_km2, 2),
        centroid=centroid,
        bbox=bbox,
        is_predefined=False,
        created_at=now,
    )
    return SuccessResponse(data={"area": res.model_dump()})


@router.get("/{area_id}", response_model=SuccessResponse)
def get_area(area_id: str):
    """Retrieve details for a specific Area of Interest."""
    with database.get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, name, geometry, area_sq_km, centroid_lat, centroid_lon,
                   bbox_west, bbox_south, bbox_east, bbox_north, is_predefined, created_at
            FROM areas_of_interest
            WHERE id = ?
            """,
            (area_id,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area of Interest not found")

        area = AOIResponse(
            id=row["id"],
            name=row["name"],
            geometry=json.loads(row["geometry"]),
            area_sq_km=row["area_sq_km"],
            centroid={"lat": row["centroid_lat"], "lng": row["centroid_lon"]},
            bbox={
                "west": row["bbox_west"],
                "south": row["bbox_south"],
                "east": row["bbox_east"],
                "north": row["bbox_north"],
            },
            is_predefined=bool(row["is_predefined"]),
            created_at=row["created_at"],
        )

    return SuccessResponse(data={"area": area.model_dump()})


@router.delete("/{area_id}", response_model=SuccessResponse)
def delete_area(area_id: str):
    """Delete a custom Area of Interest (predefined areas are protected)."""
    with database.get_connection() as conn:
        row = conn.execute(
            "SELECT is_predefined FROM areas_of_interest WHERE id = ?",
            (area_id,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area of Interest not found")
        if row["is_predefined"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Predefined reference study areas cannot be deleted",
            )

        conn.execute("DELETE FROM areas_of_interest WHERE id = ?", (area_id,))

    return SuccessResponse(data={"deleted_id": area_id})
