"""Deterministic demonstration data generator.

Generates synthetic but spatially coherent Sentinel-2 surface reflectance
bands for any AOI. The output is deterministic: the same geometry and date
always produce the same arrays. This is clearly labelled as DEMONSTRATION
DATA throughout the application.

The generator creates realistic spectral patterns by combining:
- A base landscape gradient seeded from the AOI centroid
- Land-cover regions (vegetation, water, built-up, bare soil) positioned
  using deterministic spatial functions
- Seasonal variation derived from the requested date
- Gaussian noise for texture

The spectral reflectance values are physically plausible for Sentinel-2
surface reflectance (0-1 scale) in Kenyan landscapes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

import numpy as np
from shapely.geometry import shape

import config

# Grid size for demo rasters
SIZE = config.DEMO_RASTER_SIZE

# Typical surface reflectance ranges by land-cover class (Sentinel-2, 0-1)
_SPECTRA = {
    #                 Red    Green   NIR    SWIR
    "vegetation":   (0.04,  0.07,  0.42,  0.15),
    "dense_veg":    (0.03,  0.06,  0.52,  0.12),
    "cropland":     (0.06,  0.09,  0.35,  0.18),
    "water":        (0.04,  0.06,  0.02,  0.01),
    "built_up":     (0.14,  0.12,  0.18,  0.22),
    "bare_soil":    (0.22,  0.18,  0.28,  0.30),
}


@dataclass
class SpectralBands:
    """Container for multi-band reflectance data."""

    red: np.ndarray       # shape (H, W), float32, 0-1
    green: np.ndarray
    nir: np.ndarray
    swir: np.ndarray
    bounds: tuple         # (west, south, east, north) in EPSG:4326
    crs: str
    nodata: float
    resolution_m: float
    acquisition_date: str
    cloud_cover_pct: float
    quality_mask: np.ndarray  # 0=invalid, 1=valid, 2=cloud


def _geometry_seed(geojson: dict, date_str: str) -> int:
    """Derive a deterministic seed from geometry + date."""
    raw = f"{geojson.get('type')}-{str(geojson.get('coordinates'))}-{date_str}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return int(digest[:8], 16)


def _seasonal_factor(date_str: str) -> float:
    """Seasonal modulation: greener in long rains (Mar-May), drier Jul-Sep.

    Returns a multiplier in [0.7, 1.3] that shifts vegetation vigour.
    Kenya has bimodal rainfall: long rains (March-May), short rains (Oct-Dec).
    """
    d = date.fromisoformat(date_str)
    day_of_year = d.timetuple().tm_yday
    # Peak greenness around day 120 (April) and day 305 (November)
    phase1 = np.cos(2 * np.pi * (day_of_year - 120) / 365)
    phase2 = np.cos(2 * np.pi * (day_of_year - 305) / 365) * 0.6
    modulation = 0.25 * max(phase1, phase2)
    return 1.0 + modulation


def _make_landscape(rng: np.random.Generator, size: int) -> np.ndarray:
    """Create a smooth landscape classification map.

    Returns a float array in [0, 1] where:
    0.0 - 0.15 : water
    0.15 - 0.35: built-up
    0.35 - 0.55: bare soil / cropland transition
    0.55 - 0.75: cropland
    0.75 - 1.0 : vegetation / forest
    """
    # Low-frequency base (smooth gradients)
    y_grad = np.linspace(0, 1, size).reshape(-1, 1)
    x_grad = np.linspace(0, 1, size).reshape(1, -1)

    # Deterministic pseudo-terrain from multiple frequency components
    freq1 = rng.uniform(1.5, 3.0)
    freq2 = rng.uniform(2.0, 4.0)
    phase1 = rng.uniform(0, 2 * np.pi)
    phase2 = rng.uniform(0, 2 * np.pi)
    offset_x = rng.uniform(0.2, 0.8)
    offset_y = rng.uniform(0.2, 0.8)

    landscape = (
        0.3 * np.sin(freq1 * np.pi * y_grad + phase1)
        + 0.2 * np.cos(freq2 * np.pi * x_grad + phase2)
        + 0.15 * np.sin(2.5 * np.pi * (y_grad - offset_y))
        * np.cos(1.8 * np.pi * (x_grad - offset_x))
        + 0.1 * rng.standard_normal((size, size)).astype(np.float32)
    )

    # Normalise to [0, 1]
    landscape = landscape - landscape.min()
    landscape = landscape / (landscape.max() + 1e-10)

    # Add a water body feature (circular)
    cy, cx = int(size * offset_y), int(size * offset_x)
    radius = int(size * rng.uniform(0.05, 0.12))
    yy, xx = np.ogrid[:size, :size]
    water_mask = ((yy - cy) ** 2 + (xx - cx) ** 2) < radius ** 2
    landscape[water_mask] = rng.uniform(0.0, 0.10)

    return landscape.astype(np.float32)


def _reflectance_from_landscape(
    landscape: np.ndarray,
    band_index: int,
    season: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Map landscape values to surface reflectance for a spectral band.

    band_index: 0=red, 1=green, 2=nir, 3=swir
    """
    result = np.zeros_like(landscape)

    # Define thresholds for land-cover mapping
    classes = [
        (0.00, 0.15, "water"),
        (0.15, 0.30, "built_up"),
        (0.30, 0.45, "bare_soil"),
        (0.45, 0.65, "cropland"),
        (0.65, 0.85, "vegetation"),
        (0.85, 1.01, "dense_veg"),
    ]

    for lo, hi, lc_name in classes:
        mask = (landscape >= lo) & (landscape < hi)
        base_val = _SPECTRA[lc_name][band_index]

        # Apply seasonal modulation for vegetation bands
        if lc_name in ("vegetation", "dense_veg", "cropland") and band_index == 2:
            base_val *= season  # NIR increases with vegetation vigour
        if lc_name in ("vegetation", "dense_veg", "cropland") and band_index == 0:
            base_val /= season  # Red decreases (more absorption)

        noise = rng.normal(0, 0.01, size=mask.sum()).astype(np.float32)
        result[mask] = np.clip(base_val + noise, 0.001, 0.999)

    # Smooth transitions between classes
    from scipy.ndimage import uniform_filter
    try:
        result = uniform_filter(result, size=3)
    except ImportError:
        pass  # Skip smoothing if scipy unavailable

    return np.clip(result, 0.001, 0.999).astype(np.float32)


def _generate_quality_mask(
    rng: np.random.Generator,
    size: int,
    cloud_pct: float,
) -> np.ndarray:
    """Generate a data quality mask.

    0 = invalid/nodata, 1 = valid, 2 = cloud
    """
    mask = np.ones((size, size), dtype=np.uint8)

    if cloud_pct > 0:
        # Cloud patches as elliptical regions
        n_clouds = max(1, int(cloud_pct / 8))
        for _ in range(n_clouds):
            cy = rng.integers(0, size)
            cx = rng.integers(0, size)
            ry = rng.integers(size // 20, size // 6)
            rx = rng.integers(size // 20, size // 6)
            yy, xx = np.ogrid[:size, :size]
            cloud_region = ((yy - cy) / (ry + 1)) ** 2 + ((xx - cx) / (rx + 1)) ** 2 < 1
            mask[cloud_region] = 2

    return mask


def generate_demo_bands(
    geojson: dict,
    date_str: str,
    seed_offset: int = 0,
) -> SpectralBands:
    """Generate deterministic demonstration spectral bands for an AOI.

    Parameters
    ----------
    geojson : dict
        GeoJSON geometry (Polygon or MultiPolygon).
    date_str : str
        ISO-8601 date (e.g. "2024-03-15").
    seed_offset : int
        Added to the base seed for generating different observations
        of the same AOI (e.g. different dates in a time series).

    Returns
    -------
    SpectralBands
        Container with red, green, NIR, SWIR arrays and metadata.
    """
    seed = _geometry_seed(geojson, date_str) + seed_offset
    rng = np.random.default_rng(seed)

    geom = shape(geojson)
    west, south, east, north = geom.bounds
    season = _seasonal_factor(date_str)

    landscape = _make_landscape(rng, SIZE)

    red = _reflectance_from_landscape(landscape, 0, season, rng)
    green = _reflectance_from_landscape(landscape, 1, season, rng)
    nir = _reflectance_from_landscape(landscape, 2, season, rng)
    swir = _reflectance_from_landscape(landscape, 3, season, rng)

    # Approximate cloud cover (low for demo, realistic range)
    cloud_pct = float(rng.uniform(2, 18))
    quality = _generate_quality_mask(rng, SIZE, cloud_pct)

    # Apply cloud masking: set clouded pixels to NaN
    cloud_mask = quality == 2
    red[cloud_mask] = np.nan
    green[cloud_mask] = np.nan
    nir[cloud_mask] = np.nan
    swir[cloud_mask] = np.nan

    # Approximate resolution based on AOI size
    extent_km = max(
        (east - west) * 111.32 * np.cos(np.radians((north + south) / 2)),
        (north - south) * 111.32,
    )
    resolution_m = (extent_km * 1000) / SIZE

    return SpectralBands(
        red=red,
        green=green,
        nir=nir,
        swir=swir,
        bounds=(west, south, east, north),
        crs="EPSG:4326",
        nodata=float("nan"),
        resolution_m=round(resolution_m, 1),
        acquisition_date=date_str,
        cloud_cover_pct=round(cloud_pct, 1),
        quality_mask=quality,
    )


def generate_timeseries_dates(start: str, end: str, interval_days: int = 16) -> list[str]:
    """Generate observation dates between start and end.

    Uses Sentinel-2 revisit interval (approximately 5 days for the
    constellation, but we use 16-day composites for cleaner demo data).
    """
    from datetime import timedelta
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    dates = []
    current = s
    while current <= e:
        dates.append(current.isoformat())
        current += timedelta(days=interval_days)
    return dates
