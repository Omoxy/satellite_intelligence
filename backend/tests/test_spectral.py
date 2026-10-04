"""Unit tests for spectral indices.

Verifies:
- Formula implementations for NDVI, NDMI, NDWI, NDBI
- Bounded output within [-1.0, 1.0]
- Safe division-by-zero handling returning NaN
- Correct index dispatching
"""

import numpy as np
import pytest

from engine import spectral


def test_ndvi_calculation():
    """NDVI = (NIR - Red) / (NIR + Red)."""
    nir = np.array([[0.8, 0.5], [0.1, 0.4]], dtype=np.float32)
    red = np.array([[0.2, 0.1], [0.2, 0.4]], dtype=np.float32)

    result = spectral.calculate_ndvi(nir, red)

    # (0.8 - 0.2) / (0.8 + 0.2) = 0.6 / 1.0 = 0.6
    assert pytest.approx(result[0, 0], 1e-4) == 0.6
    # (0.5 - 0.1) / (0.5 + 0.1) = 0.4 / 0.6 ≈ 0.6667
    assert pytest.approx(result[0, 1], 1e-4) == 0.66667
    # (0.1 - 0.2) / (0.1 + 0.2) = -0.1 / 0.3 ≈ -0.3333
    assert pytest.approx(result[1, 0], 1e-4) == -0.33333
    # (0.4 - 0.4) / (0.4 + 0.4) = 0.0
    assert pytest.approx(result[1, 1], 1e-4) == 0.0


def test_ndmi_calculation():
    """NDMI = (NIR - SWIR) / (NIR + SWIR)."""
    nir = np.array([[0.7]], dtype=np.float32)
    swir = np.array([[0.3]], dtype=np.float32)
    result = spectral.calculate_ndmi(nir, swir)
    # (0.7 - 0.3) / (0.7 + 0.3) = 0.4
    assert pytest.approx(result[0, 0], 1e-4) == 0.4


def test_ndwi_calculation():
    """NDWI = (Green - NIR) / (Green + NIR)."""
    green = np.array([[0.6]], dtype=np.float32)
    nir = np.array([[0.2]], dtype=np.float32)
    result = spectral.calculate_ndwi(green, nir)
    # (0.6 - 0.2) / (0.6 + 0.2) = 0.5
    assert pytest.approx(result[0, 0], 1e-4) == 0.5


def test_ndbi_calculation():
    """NDBI = (SWIR - NIR) / (SWIR + NIR)."""
    swir = np.array([[0.6]], dtype=np.float32)
    nir = np.array([[0.3]], dtype=np.float32)
    result = spectral.calculate_ndbi(swir, nir)
    # (0.6 - 0.3) / (0.6 + 0.3) = 0.3 / 0.9 ≈ 0.3333
    assert pytest.approx(result[0, 0], 1e-4) == 0.33333


def test_division_by_zero_handling():
    """Denominator = 0 must return NaN without throwing an unhandled exception."""
    nir = np.array([[0.0]], dtype=np.float32)
    red = np.array([[0.0]], dtype=np.float32)
    result = spectral.calculate_ndvi(nir, red)
    assert np.isnan(result[0, 0])


def test_index_dispatcher():
    bands = {
        "red": np.array([[0.1]], dtype=np.float32),
        "green": np.array([[0.2]], dtype=np.float32),
        "nir": np.array([[0.5]], dtype=np.float32),
        "swir": np.array([[0.3]], dtype=np.float32),
    }
    for ind in ["ndvi", "ndmi", "ndwi", "ndbi"]:
        res = spectral.calculate_index(ind, bands)
        assert res.shape == (1, 1)
        assert -1.0 <= res[0, 0] <= 1.0

    with pytest.raises(ValueError):
        spectral.calculate_index("invalid_index", bands)
