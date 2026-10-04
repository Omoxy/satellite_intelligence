"""Rule-based land-cover classification from spectral indices.

This is a threshold-based classification, not machine learning.
Thresholds are derived from published remote-sensing literature for
tropical/equatorial regions (East Africa).

Classes
-------
- Water        : NDWI > 0.2
- Built-up     : NDBI > 0.1 and NDVI < 0.2
- Bare land    : NDVI < 0.15 and NDBI <= 0.1
- Cropland     : 0.2 <= NDVI < 0.45 and NDWI < 0.1
- Vegetation   : NDVI >= 0.45

Limitations
-----------
- No training data or supervised learning is used.
- Accuracy depends on threshold appropriateness for the specific scene.
- Mixed pixels at class boundaries may be misclassified.
- Cloud-covered pixels are excluded (set to NoData).
"""

from __future__ import annotations

import numpy as np

# Class labels and their display names
LAND_COVER_CLASSES = {
    1: "Water",
    2: "Built-up",
    3: "Bare land",
    4: "Cropland",
    5: "Vegetation",
    0: "Unclassified",
}


def classify_land_cover(
    ndvi: np.ndarray,
    ndwi: np.ndarray,
    ndbi: np.ndarray,
) -> dict:
    """Apply rule-based classification to spectral index arrays.

    Parameters
    ----------
    ndvi, ndwi, ndbi : ndarray, float32
        Same-shape 2D arrays. NaN = NoData.

    Returns
    -------
    dict with keys:
        class_map : ndarray int8 (pixel class codes)
        class_areas : list of {class_name, area_pct, pixel_count}
    """
    h, w = ndvi.shape
    class_map = np.zeros((h, w), dtype=np.int8)

    # Mask where all indices have valid data
    valid = ~np.isnan(ndvi) & ~np.isnan(ndwi) & ~np.isnan(ndbi)

    # Apply rules in priority order (water first, vegetation last)
    water = valid & (ndwi > 0.2)
    class_map[water] = 1

    built_up = valid & ~water & (ndbi > 0.1) & (ndvi < 0.2)
    class_map[built_up] = 2

    bare = valid & ~water & ~built_up & (ndvi < 0.15) & (ndbi <= 0.1)
    class_map[bare] = 3

    vegetation = valid & ~water & ~built_up & ~bare & (ndvi >= 0.45)
    class_map[vegetation] = 5

    cropland = valid & ~water & ~built_up & ~bare & ~vegetation
    class_map[cropland] = 4

    # Compute area percentages
    total_valid = int(valid.sum())
    class_areas = []
    for code, name in LAND_COVER_CLASSES.items():
        if code == 0:
            continue
        count = int((class_map == code).sum())
        pct = round(count / total_valid * 100, 1) if total_valid > 0 else 0.0
        class_areas.append({
            "class_name": name,
            "area_pct": pct,
            "pixel_count": count,
        })

    return {
        "class_map": class_map,
        "class_areas": class_areas,
    }
