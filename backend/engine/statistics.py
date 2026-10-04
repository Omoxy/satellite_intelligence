"""Zonal statistics for raster arrays.

Computes mean, min, max, standard deviation, pixel count, NoData count,
and histogram for a 2D float32 array.
"""

from __future__ import annotations

import numpy as np


def compute_statistics(data: np.ndarray) -> dict:
    """Compute zonal statistics for a 2D raster array.

    Parameters
    ----------
    data : ndarray, float32
        2D array where NaN represents NoData.

    Returns
    -------
    dict with keys: mean, min, max, std, pixel_count, nodata_count, histogram.
    """
    valid = data[~np.isnan(data)]
    total = data.size
    nodata = total - valid.size

    if valid.size == 0:
        return {
            "mean": None,
            "min": None,
            "max": None,
            "std": None,
            "pixel_count": 0,
            "nodata_count": total,
            "histogram": {"bins": [], "counts": []},
        }

    hist_counts, hist_edges = np.histogram(valid, bins=20)

    return {
        "mean": round(float(np.mean(valid)), 4),
        "min": round(float(np.min(valid)), 4),
        "max": round(float(np.max(valid)), 4),
        "std": round(float(np.std(valid)), 4),
        "pixel_count": int(valid.size),
        "nodata_count": int(nodata),
        "histogram": {
            "bins": [round(float(e), 4) for e in hist_edges],
            "counts": [int(c) for c in hist_counts],
        },
    }
