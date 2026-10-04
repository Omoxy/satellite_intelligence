"""Generate genuine, spatially-referenced multi-band GeoTIFF rasters for reference study areas.

Output specifications:
- Format: GeoTIFF (Cloud-Optimized, tiled, LZW compressed)
- CRS: EPSG:4326 (WGS84 decimal degrees)
- 5 Bands:
    Band 1: Blue (B2, ~490 nm)
    Band 2: Green (B3, ~560 nm)
    Band 3: Red (B4, ~665 nm)
    Band 4: NIR (B8, ~842 nm)
    Band 5: SWIR-1 (B11, ~1610 nm)
- Data type: Float32 (surface reflectance scaled 0.0 - 1.0)
- NoData value: -9999.0
- Deterministic: Built with explicit spatial seeds and physical biome functions
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "backend" / "data" / "rasters"
STUDY_AREAS_FILE = ROOT_DIR / "backend" / "data" / "study_areas.json"

# Surface reflectance profiles by land cover class (Blue, Green, Red, NIR, SWIR)
SPECTRAL_PROFILES = {
    "dense_forest": (0.02, 0.05, 0.03, 0.58, 0.12),
    "cropland":     (0.04, 0.08, 0.06, 0.40, 0.18),
    "grassland":    (0.05, 0.09, 0.08, 0.32, 0.22),
    "built_up":     (0.12, 0.14, 0.16, 0.18, 0.28),
    "bare_soil":    (0.14, 0.18, 0.22, 0.28, 0.34),
    "water":        (0.06, 0.07, 0.04, 0.01, 0.005),
}


def make_spatial_landscape(
    name: str,
    west: float,
    south: float,
    east: float,
    north: float,
    width: int,
    height: int,
    date_str: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate 5 physically plausible spectral bands for a specific geographic extent."""
    xs = np.linspace(west, east, width)
    ys = np.linspace(north, south, height)
    xx, yy = np.meshgrid(xs, ys)

    # Deterministic spatial seeds based on name
    seed = sum(ord(c) for c in name) + int(date_str.replace("-", "")[:6])
    rng = np.random.default_rng(seed)

    # Seasonal modifier: March is post-rain onset (greener), January is dry
    month = int(date_str.split("-")[1])
    is_wet_season = month in (3, 4, 5, 10, 11)
    season_factor = 1.25 if is_wet_season else 0.85

    # Initialize band arrays
    blue = np.full((height, width), 0.04, dtype=np.float32)
    green = np.full((height, width), 0.07, dtype=np.float32)
    red = np.full((height, width), 0.06, dtype=np.float32)
    nir = np.full((height, width), 0.35, dtype=np.float32)
    swir = np.full((height, width), 0.18, dtype=np.float32)

    # Spatial features specific to each Kenyan study area
    if "nairobi" in name.lower():
        # Central business district & urban core (south-central)
        dist_cbd = np.sqrt((xx - 36.82) ** 2 + (yy - (-1.29)) ** 2)
        urban_mask = dist_cbd < 0.06
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[urban_mask] = SPECTRAL_PROFILES["built_up"][i]

        # Nairobi National Park (south)
        park_mask = (yy < -1.33) & (xx > 36.80) & ~urban_mask
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[park_mask] = SPECTRAL_PROFILES["grassland"][i]

        # Karura Forest / Northern Highlands (north)
        forest_mask = (yy > -1.24) & (xx < 36.85) & ~urban_mask
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[forest_mask] = SPECTRAL_PROFILES["dense_forest"][i]

        # Nairobi Dam / Ruiru water feature
        water_mask = np.sqrt((xx - 36.80) ** 2 + (yy - (-1.31)) ** 2) < 0.015
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[water_mask] = SPECTRAL_PROFILES["water"][i]

    elif "nakuru" in name.lower():
        # Lake Nakuru open alkaline water body (center)
        lake_mask = ((xx - 36.08) / 0.04) ** 2 + ((yy - (-0.35)) / 0.06) ** 2 < 1.0
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[lake_mask] = SPECTRAL_PROFILES["water"][i]

        # Menengai Crater & Caldera (north)
        crater_mask = ((xx - 36.07) / 0.03) ** 2 + ((yy - (-0.20)) / 0.03) ** 2 < 1.0
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[crater_mask] = SPECTRAL_PROFILES["bare_soil"][i]

        # Urban Nakuru town (north-west of lake)
        town_mask = (xx > 36.04) & (xx < 36.09) & (yy > -0.30) & (yy < -0.26)
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[town_mask] = SPECTRAL_PROFILES["built_up"][i]

    elif "murang" in name.lower():
        # Highland Tea & Coffee Montane Zone
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[:] = SPECTRAL_PROFILES["dense_forest"][i]
        # Lowland mixed agriculture transition
        lowland = xx > 37.05
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[lowland] = SPECTRAL_PROFILES["cropland"][i]

    elif "siaya" in name.lower():
        # Lake Victoria Bay / Shoreline
        bay_mask = (xx < 34.20) & (yy < -0.05)
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[bay_mask] = SPECTRAL_PROFILES["water"][i]
        # Yala Swamp / Wetland corridor
        swamp_mask = (yy > -0.02) & (yy < 0.04) & (xx > 34.15) & (xx < 34.30)
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[swamp_mask] = SPECTRAL_PROFILES["dense_forest"][i]

    elif "elgeyo" in name.lower():
        # Cherangani Hills High Montane Forest (east)
        hills_mask = xx > 35.55
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[hills_mask] = SPECTRAL_PROFILES["dense_forest"][i]
        # Kerio Valley Floor (dry savanna / acacia)
        valley_mask = xx <= 35.55
        for i, b_arr in enumerate([blue, green, red, nir, swir]):
            b_arr[valley_mask] = SPECTRAL_PROFILES["grassland"][i]

    # Apply seasonal modulation
    nir = np.clip(nir * season_factor, 0.01, 0.95)
    red = np.clip(red / (season_factor ** 0.5), 0.01, 0.95)

    # Subtle spatial texture
    noise = rng.normal(0, 0.005, (height, width)).astype(np.float32)
    blue = np.clip(blue + noise, 0.005, 0.95)
    green = np.clip(green + noise, 0.005, 0.95)
    red = np.clip(red + noise, 0.005, 0.95)
    nir = np.clip(nir + noise, 0.005, 0.95)
    swir = np.clip(swir + noise, 0.005, 0.95)

    return blue, green, red, nir, swir


def generate_geotiff(
    name: str,
    slug: str,
    west: float,
    south: float,
    east: float,
    north: float,
    date_str: str,
    width: int = 300,
    height: int = 300,
) -> Path:
    """Generate and write a multi-band GeoTIFF using Rasterio."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"{slug}_{date_str}.tif"

    blue, green, red, nir, swir = make_spatial_landscape(
        name, west, south, east, north, width, height, date_str
    )

    transform = from_bounds(west, south, east, north, width, height)

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 5,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": -9999.0,
        "compress": "lzw",
        "tiled": True,
        "blockxsize": 128,
        "blockysize": 128,
    }

    with rasterio.open(out_file, "w", **profile) as dst:
        dst.write(blue, 1)
        dst.write(green, 2)
        dst.write(red, 3)
        dst.write(nir, 4)
        dst.write(swir, 5)

        # Set band descriptions
        dst.set_band_description(1, "B02_Blue_490nm")
        dst.set_band_description(2, "B03_Green_560nm")
        dst.set_band_description(3, "B04_Red_665nm")
        dst.set_band_description(4, "B08_NIR_842nm")
        dst.set_band_description(5, "B11_SWIR1_1610nm")

        dst.update_tags(
            title=f"Synthetic Sentinel-2 Surface Reflectance for {name}",
            acquisition_date=date_str,
            sensor="MSI Level-2A Synthesis",
            provenance="Deterministic biophysical landscape synthesis for portfolio demonstration",
        )

    print(f"Created GeoTIFF: {out_file.name} ({width}x{height}, 5 bands, EPSG:4326)")
    return out_file


def main():
    with open(STUDY_AREAS_FILE, "r", encoding="utf-8") as f:
        areas_data = json.load(f)

    # Distinct observation dates
    dates = ["2024-01-01", "2024-03-15", "2023-04-15", "2023-08-15", "2023-11-15"]

    print("Building spatially-referenced multi-band GeoTIFF rasters with Rasterio...")
    for feat in areas_data["features"]:
        name = feat["properties"]["name"]
        slug = name.lower().replace(" ", "_").replace("'", "")
        coords = feat["geometry"]["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        west, south, east, north = min(lons), min(lats), max(lons), max(lats)

        for d in dates:
            generate_geotiff(name, slug, west, south, east, north, d)

    print(f"All GeoTIFF rasters created in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
