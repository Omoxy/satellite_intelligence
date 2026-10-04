"""Unit tests for anomaly detection."""

import numpy as np
import pytest

from engine import anomaly


def test_baseline_computation():
    obs1 = np.array([[0.4, 0.6]], dtype=np.float32)
    obs2 = np.array([[0.6, 0.4]], dtype=np.float32)
    baseline = anomaly.compute_baseline([obs1, obs2])

    assert pytest.approx(baseline["mean"][0, 0], 1e-4) == 0.5
    assert pytest.approx(baseline["mean"][0, 1], 1e-4) == 0.5
    assert baseline["count"] == 2


def test_anomaly_classification():
    # Mean: 0.5, Std: 0.1
    b_mean = np.array([[0.5]], dtype=np.float32)
    b_std = np.array([[0.1]], dtype=np.float32)

    # 1. Normal (current = 0.52 -> z = 0.2)
    res_normal = anomaly.detect_anomalies(np.array([[0.52]], dtype=np.float32), b_mean, b_std, "ndvi")
    assert res_normal["classification"] == "normal"
    assert "No anomaly detected" in res_normal["description"]

    # 2. Watch (current = 0.62 -> z = 1.2)
    res_watch = anomaly.detect_anomalies(np.array([[0.62]], dtype=np.float32), b_mean, b_std, "ndvi")
    assert res_watch["classification"] == "watch"

    # 3. Warning (current = 0.66 -> z = 1.6)
    res_warn = anomaly.detect_anomalies(np.array([[0.66]], dtype=np.float32), b_mean, b_std, "ndvi")
    assert res_warn["classification"] == "warning"

    # 4. Alert (current = 0.25 -> z = -2.5)
    res_alert = anomaly.detect_anomalies(np.array([[0.25]], dtype=np.float32), b_mean, b_std, "ndvi")
    assert res_alert["classification"] == "alert"
    assert "Significant" in res_alert["description"]
