"""Spectral index calculations.

All indices use the normalised difference formula: (A - B) / (A + B).
Band assignments follow Sentinel-2 MSI conventions:

    B3  = Green   (560 nm)
    B4  = Red     (665 nm)
    B8  = NIR     (842 nm)
    B11 = SWIR-1  (1610 nm)

Every function operates on NumPy float32 arrays and handles division by
zero by returning NaN for undefined pixels.

References
----------
Rouse et al. (1974)  — NDVI
Gao (1996)           — NDMI (NDWI-1610)
McFeeters (1996)     — NDWI
Zha et al. (2003)    — NDBI
"""

from __future__ import annotations

import numpy as np

# Minimum denominator to avoid division-by-zero artefacts
_EPSILON = 1e-10


def _normalised_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute (A - B) / (A + B) with NaN where the denominator is zero.

    Parameters
    ----------
    a, b : ndarray, float32
        Reflectance arrays of identical shape.

    Returns
    -------
    ndarray, float32
        Values in [-1, 1] with NaN for undefined pixels.
    """
    numerator = a.astype(np.float32) - b.astype(np.float32)
    denominator = a.astype(np.float32) + b.astype(np.float32)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(
            np.abs(denominator) > _EPSILON,
            numerator / denominator,
            np.nan,
        )
    return result.astype(np.float32)


def calculate_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Normalised Difference Vegetation Index.

    NDVI = (NIR - Red) / (NIR + Red)
    Sentinel-2: (B8 - B4) / (B8 + B4)

    Interpretation
    --------------
    < 0    : water, cloud shadow, snow
    0 - 0.1: bare soil, rock
    0.1-0.3: sparse vegetation, grassland
    0.3-0.6: moderate vegetation, crops
    0.6-0.9: dense vegetation, forest
    """
    return _normalised_difference(nir, red)


def calculate_ndmi(nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """Normalised Difference Moisture Index.

    NDMI = (NIR - SWIR) / (NIR + SWIR)
    Sentinel-2: (B8 - B11) / (B8 + B11)

    Interpretation
    --------------
    < -0.2 : very dry / bare soil
    -0.2-0  : low moisture stress
    0 - 0.2 : moderate moisture
    0.2-0.4 : adequate moisture
    > 0.4   : high moisture / water bodies
    """
    return _normalised_difference(nir, swir)


def calculate_ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Normalised Difference Water Index.

    NDWI = (Green - NIR) / (Green + NIR)
    Sentinel-2: (B3 - B8) / (B3 + B8)

    Interpretation
    --------------
    < 0    : non-water surface
    0 - 0.2: possible moisture / wet soil
    0.2-0.5: water surface likely
    > 0.5  : open water
    """
    return _normalised_difference(green, nir)


def calculate_ndbi(swir: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Normalised Difference Built-up Index.

    NDBI = (SWIR - NIR) / (SWIR + NIR)
    Sentinel-2: (B11 - B8) / (B11 + B8)

    Interpretation
    --------------
    < -0.2 : dense vegetation
    -0.2-0 : moderate vegetation / agriculture
    0 - 0.2: sparse vegetation / bare soil
    > 0.2  : built-up surface
    """
    return _normalised_difference(swir, nir)


def calculate_index(indicator: str, bands: dict[str, np.ndarray]) -> np.ndarray:
    """Dispatch to the correct index function by name.

    Parameters
    ----------
    indicator : str
        One of "ndvi", "ndmi", "ndwi", "ndbi".
    bands : dict
        Keys "red", "green", "nir", "swir" mapping to float32 arrays.

    Returns
    -------
    ndarray
        The computed spectral index.

    Raises
    ------
    ValueError
        If the indicator name is not recognised.
    """
    dispatch = {
        "ndvi": lambda: calculate_ndvi(bands["nir"], bands["red"]),
        "ndmi": lambda: calculate_ndmi(bands["nir"], bands["swir"]),
        "ndwi": lambda: calculate_ndwi(bands["green"], bands["nir"]),
        "ndbi": lambda: calculate_ndbi(bands["swir"], bands["nir"]),
    }
    fn = dispatch.get(indicator)
    if fn is None:
        raise ValueError(f"Unknown indicator '{indicator}'. Supported: {sorted(dispatch)}")
    return fn()
