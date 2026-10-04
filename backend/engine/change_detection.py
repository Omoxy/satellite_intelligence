"""Change detection between two time periods.

Compares spectral index values from two periods and computes:
- Absolute change (period2 - period1)
- Percentage change where mathematically valid
- Spatial classification into increase / decrease / stable
"""

from __future__ import annotations

import numpy as np


# Minimum absolute change to consider a pixel non-stable
CHANGE_THRESHOLD = 0.05


def compute_change(
    period1: np.ndarray,
    period2: np.ndarray,
    threshold: float = CHANGE_THRESHOLD,
) -> dict:
    """Compute change between two raster arrays of the same index.

    Parameters
    ----------
    period1, period2 : ndarray, float32
        Same-shape arrays. NaN = NoData.
    threshold : float
        Absolute change below this is classified as stable.

    Returns
    -------
    dict with keys:
        absolute_change : ndarray
        percentage_change : ndarray (NaN where period1 == 0)
        change_class : ndarray (int8: -1=decrease, 0=stable, 1=increase)
        period1_mean, period2_mean : float
        abs_change_mean : float
        pct_change_mean : float or None
        increase_pct, decrease_pct, stable_pct : float
    """
    # Both must have valid data
    valid_mask = ~np.isnan(period1) & ~np.isnan(period2)
    p1 = np.where(valid_mask, period1, np.nan)
    p2 = np.where(valid_mask, period2, np.nan)

    abs_change = p2 - p1

    # Percentage change: only where period1 is meaningfully non-zero
    with np.errstate(divide="ignore", invalid="ignore"):
        pct_change = np.where(
            (np.abs(p1) > 0.01) & valid_mask,
            (abs_change / np.abs(p1)) * 100,
            np.nan,
        )

    # Classify pixels
    change_class = np.zeros_like(abs_change, dtype=np.int8)
    change_class[abs_change > threshold] = 1   # increase
    change_class[abs_change < -threshold] = -1  # decrease
    change_class[~valid_mask] = 0

    # Summary statistics
    valid_abs = abs_change[valid_mask]
    valid_pct = pct_change[~np.isnan(pct_change)]
    valid_class = change_class[valid_mask]
    n_valid = valid_mask.sum()

    if n_valid == 0:
        return {
            "absolute_change": abs_change,
            "percentage_change": pct_change,
            "change_class": change_class,
            "period1_mean": None,
            "period2_mean": None,
            "abs_change_mean": None,
            "pct_change_mean": None,
            "increase_pct": 0.0,
            "decrease_pct": 0.0,
            "stable_pct": 100.0,
        }

    increase_count = int((valid_class == 1).sum())
    decrease_count = int((valid_class == -1).sum())
    stable_count = int((valid_class == 0).sum())

    return {
        "absolute_change": abs_change,
        "percentage_change": pct_change,
        "change_class": change_class,
        "period1_mean": round(float(np.nanmean(p1)), 4),
        "period2_mean": round(float(np.nanmean(p2)), 4),
        "abs_change_mean": round(float(np.mean(valid_abs)), 4),
        "pct_change_mean": (
            round(float(np.mean(valid_pct)), 2) if valid_pct.size > 0 else None
        ),
        "increase_pct": round(increase_count / n_valid * 100, 1),
        "decrease_pct": round(decrease_count / n_valid * 100, 1),
        "stable_pct": round(stable_count / n_valid * 100, 1),
    }
