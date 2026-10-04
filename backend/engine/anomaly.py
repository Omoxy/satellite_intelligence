"""Statistical anomaly detection for spectral indices.

Methodology
-----------
1. Compute a baseline (historical mean and standard deviation) from a
   set of observations.
2. Compare the current observation against the baseline.
3. Classify the deviation using configurable sigma thresholds.

This is a transparent, reproducible statistical method. It does NOT
claim ground-truth crop failure or ecological events. Outputs are
labelled as "potential anomaly detected" per responsible EO practice.
"""

from __future__ import annotations

import warnings

import numpy as np


# Sigma thresholds for anomaly classification
SIGMA_WATCH = 1.0    # 1σ deviation
SIGMA_WARNING = 1.5  # 1.5σ deviation
SIGMA_ALERT = 2.0    # 2σ deviation


def compute_baseline(
    observations: list[np.ndarray],
) -> dict:
    """Compute per-pixel baseline statistics from multiple observations.

    Parameters
    ----------
    observations : list of ndarray
        List of 2D float32 arrays (same shape). NaN = NoData.

    Returns
    -------
    dict with keys: mean (ndarray), std (ndarray), count (int).
    """
    if not observations:
        return {"mean": None, "std": None, "count": 0}

    stack = np.stack(observations, axis=0)  # shape: (N, H, W)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        with np.errstate(all="ignore"):
            baseline_mean = np.nanmean(stack, axis=0)
            baseline_std = np.nanstd(stack, axis=0)

    # Minimum std to avoid division by near-zero
    baseline_std = np.maximum(baseline_std, 0.01)

    return {
        "mean": baseline_mean,
        "std": baseline_std,
        "count": len(observations),
    }


def detect_anomalies(
    current: np.ndarray,
    baseline_mean: np.ndarray,
    baseline_std: np.ndarray,
    indicator: str,
) -> dict:
    """Compare current observation against the baseline.

    Parameters
    ----------
    current : ndarray, float32
        Current observation (2D).
    baseline_mean, baseline_std : ndarray, float32
        Per-pixel baseline statistics (same shape as current).
    indicator : str
        Name of the spectral index for interpretive messaging.

    Returns
    -------
    dict with keys:
        deviation : ndarray (z-score per pixel)
        classification : str (overall classification)
        baseline_value : float (spatial mean of baseline)
        current_value : float (spatial mean of current)
        deviation_value : float (spatial mean z-score)
        threshold : float (sigma threshold applied)
        description : str (responsible interpretation)
        anomaly_map : ndarray int8 (0=normal, 1=watch, 2=warning, 3=alert)
    """
    valid = ~np.isnan(current) & ~np.isnan(baseline_mean)

    if valid.sum() == 0:
        return _empty_result(indicator)

    deviation = np.full_like(current, np.nan)
    deviation[valid] = (current[valid] - baseline_mean[valid]) / baseline_std[valid]

    # Spatial mean of the deviation
    mean_dev = float(np.nanmean(deviation))
    abs_dev = abs(mean_dev)

    # Classify
    if abs_dev >= SIGMA_ALERT:
        classification = "alert"
        threshold = SIGMA_ALERT
    elif abs_dev >= SIGMA_WARNING:
        classification = "warning"
        threshold = SIGMA_WARNING
    elif abs_dev >= SIGMA_WATCH:
        classification = "watch"
        threshold = SIGMA_WATCH
    else:
        classification = "normal"
        threshold = SIGMA_WATCH

    # Per-pixel anomaly map
    anomaly_map = np.zeros_like(current, dtype=np.int8)
    abs_deviation = np.abs(deviation)
    anomaly_map[abs_deviation >= SIGMA_WATCH] = 1
    anomaly_map[abs_deviation >= SIGMA_WARNING] = 2
    anomaly_map[abs_deviation >= SIGMA_ALERT] = 3
    anomaly_map[np.isnan(deviation)] = 0

    description = _generate_description(indicator, classification, mean_dev)

    return {
        "deviation": deviation,
        "classification": classification,
        "baseline_value": round(float(np.nanmean(baseline_mean)), 4),
        "current_value": round(float(np.nanmean(current)), 4),
        "deviation_value": round(mean_dev, 4),
        "threshold": threshold,
        "description": description,
        "anomaly_map": anomaly_map,
    }


def _generate_description(indicator: str, classification: str, deviation: float) -> str:
    """Generate a responsible interpretive description.

    Language avoids definitive claims. EO-derived indicators are not
    ground truth.
    """
    indicator_upper = indicator.upper()
    direction = "below" if deviation < 0 else "above"

    descriptions = {
        "normal": (
            f"{indicator_upper} values are within the expected range "
            f"for this area and season. No anomaly detected."
        ),
        "watch": (
            f"{indicator_upper} values are slightly {direction} the historical "
            f"baseline (deviation: {abs(deviation):.2f}σ). This may warrant "
            f"monitoring but does not indicate a confirmed change."
        ),
        "warning": (
            f"Potential {indicator_upper} anomaly detected. Values are "
            f"{abs(deviation):.2f}σ {direction} the historical baseline. "
            f"This suggests a possible change in surface conditions. "
            f"Field verification is recommended before drawing conclusions."
        ),
        "alert": (
            f"Significant {indicator_upper} deviation detected "
            f"({abs(deviation):.2f}σ {direction} baseline). This may "
            f"indicate a substantial change in surface conditions such as "
            f"vegetation stress, land-use change, or environmental impact. "
            f"This is a remotely sensed indicator and requires ground "
            f"verification to confirm the cause."
        ),
    }
    return descriptions.get(classification, descriptions["normal"])


def _empty_result(indicator: str) -> dict:
    """Result when no valid pixels are available."""
    return {
        "deviation": None,
        "classification": "normal",
        "baseline_value": None,
        "current_value": None,
        "deviation_value": None,
        "threshold": SIGMA_WATCH,
        "description": (
            f"Insufficient valid data to assess {indicator.upper()} anomalies. "
            f"This may be due to cloud cover or missing observations."
        ),
        "anomaly_map": None,
    }
