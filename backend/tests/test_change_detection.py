"""Unit tests for multi-temporal change detection."""

import numpy as np
import pytest

from engine import change_detection


def test_compute_change_basic():
    p1 = np.array([[0.4, 0.5], [0.6, 0.2]], dtype=np.float32)
    p2 = np.array([[0.5, 0.4], [0.6, 0.1]], dtype=np.float32)

    res = change_detection.compute_change(p1, p2, threshold=0.05)

    assert pytest.approx(res["period1_mean"], 1e-4) == 0.425
    assert pytest.approx(res["period2_mean"], 1e-4) == 0.4
    assert pytest.approx(res["abs_change_mean"], 1e-4) == -0.025

    # [0, 0]: 0.5 - 0.4 = +0.1 (> 0.05 -> increase)
    assert res["change_class"][0, 0] == 1
    # [0, 1]: 0.4 - 0.5 = -0.1 (< -0.05 -> decrease)
    assert res["change_class"][0, 1] == -1
    # [1, 0]: 0.6 - 0.6 = 0.0 (stable)
    assert res["change_class"][1, 0] == 0
    # [1, 1]: 0.1 - 0.2 = -0.1 (< -0.05 -> decrease)
    assert res["change_class"][1, 1] == -1

    assert res["increase_pct"] == 25.0
    assert res["decrease_pct"] == 50.0
    assert res["stable_pct"] == 25.0


def test_compute_change_with_nan():
    p1 = np.array([[0.5, np.nan]], dtype=np.float32)
    p2 = np.array([[0.7, 0.8]], dtype=np.float32)

    res = change_detection.compute_change(p1, p2)
    assert res["period1_mean"] == 0.5
    assert res["period2_mean"] == 0.7
    assert res["increase_pct"] == 100.0


def test_compute_change_all_nan():
    p1 = np.array([[np.nan]], dtype=np.float32)
    p2 = np.array([[np.nan]], dtype=np.float32)

    res = change_detection.compute_change(p1, p2)
    assert res["period1_mean"] is None
    assert res["increase_pct"] == 0.0
    assert res["stable_pct"] == 100.0
