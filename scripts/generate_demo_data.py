"""CLI utility for generating and inspecting demonstration Sentinel-2 bands."""

import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from engine import demo_data, spectral, statistics


def main():
    parser = argparse.ArgumentParser(description="Generate demo Sentinel-2 bands for an AOI")
    parser.add_argument("--date", default="2024-03-15", help="Observation date (YYYY-MM-DD)")
    parser.add_argument("--area", default="Nairobi", help="Predefined study area name")
    args = parser.parse_args()

    study_areas_file = Path(__file__).resolve().parent.parent / "backend" / "data" / "study_areas.json"
    with open(study_areas_file, "r", encoding="utf-8") as f:
        areas = json.load(f)

    target_feature = next(
        (f for f in areas["features"] if f["properties"]["name"].lower() == args.area.lower()),
        None,
    )
    if not target_feature:
        print(f"Error: Area '{args.area}' not found in study_areas.json")
        sys.exit(1)

    geom = target_feature["geometry"]
    print(f"Generating synthetic Sentinel-2 observations for {args.area} on {args.date}...")

    bands = demo_data.generate_demo_bands(geom, args.date)
    print(f"Raster dimensions: {bands.red.shape}")
    print(f"Resolution: ~{bands.resolution_m} m/pixel")
    print(f"Cloud contamination: {bands.cloud_cover_pct}%")

    b_dict = {
        "red": bands.red,
        "green": bands.green,
        "nir": bands.nir,
        "swir": bands.swir,
    }

    for ind in ["ndvi", "ndmi", "ndwi", "ndbi"]:
        arr = spectral.calculate_index(ind, b_dict)
        stats = statistics.compute_statistics(arr)
        print(f"[{ind.upper()}] Mean: {stats['mean']}, Min: {stats['min']}, Max: {stats['max']}, Std: {stats['std']}")


if __name__ == "__main__":
    main()
