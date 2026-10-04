"""Raster rendering: convert numerical arrays to coloured PNG overlays.

Each spectral index has a scientifically appropriate colour ramp.
The renderer produces RGBA PNG images encoded as base64 data URLs
for direct use as Leaflet ImageOverlay sources.
"""

from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image


# Colour ramp definitions: list of (position, R, G, B) tuples
# Position is normalised 0-1 within the value range.

COLORMAPS = {
    "ndvi": {
        "vmin": -0.2,
        "vmax": 0.9,
        "stops": [
            (0.00, 165,   0,  38),   # deep red (water/bare)
            (0.15, 215,  48,  39),   # red
            (0.25, 244, 109,  67),   # orange
            (0.35, 253, 174,  97),   # light orange
            (0.45, 254, 224, 139),   # yellow
            (0.55, 217, 239, 139),   # yellow-green
            (0.65, 166, 217, 106),   # light green
            (0.75, 102, 189,  99),   # green
            (0.85,  26, 152,  80),   # dark green
            (1.00,   0, 104,  55),   # deep green
        ],
    },
    "ndmi": {
        "vmin": -0.4,
        "vmax": 0.6,
        "stops": [
            (0.00, 140,  81,  10),   # brown (dry)
            (0.20, 191, 129,  45),
            (0.35, 223, 194, 125),
            (0.50, 246, 232, 195),   # pale
            (0.65, 199, 234, 229),
            (0.80,  90, 180, 172),   # teal
            (0.90,   1, 133, 113),
            (1.00,   0,  60,  48),   # dark teal
        ],
    },
    "ndwi": {
        "vmin": -0.5,
        "vmax": 0.5,
        "stops": [
            (0.00, 140,  81,  10),   # brown (land)
            (0.25, 216, 179, 101),
            (0.45, 246, 232, 195),   # pale (transition)
            (0.55, 186, 228, 188),
            (0.75,  68, 135, 176),   # blue
            (1.00,   8,  48, 107),   # deep blue (water)
        ],
    },
    "ndbi": {
        "vmin": -0.3,
        "vmax": 0.4,
        "stops": [
            (0.00,   0, 104,  55),   # green (vegetation)
            (0.25, 166, 217, 106),   # light green
            (0.45, 254, 224, 139),   # yellow
            (0.60, 253, 174,  97),   # orange
            (0.80, 215,  48,  39),   # red
            (1.00, 128,   0,   0),   # dark red (built-up)
        ],
    },
    "change": {
        "vmin": -0.3,
        "vmax": 0.3,
        "stops": [
            (0.00, 178,  24,  43),   # dark red (strong decrease)
            (0.25, 239, 138,  98),   # light red
            (0.45, 253, 219, 199),   # pale red
            (0.50, 247, 247, 247),   # white (no change)
            (0.55, 209, 229, 240),   # pale blue
            (0.75,  67, 147, 195),   # light blue
            (1.00,  33, 102, 172),   # dark blue (strong increase)
        ],
    },
    "anomaly": {
        "vmin": 0,
        "vmax": 3,
        "stops": [
            (0.00, 102, 189,  99),   # green (normal)
            (0.33, 254, 224, 139),   # yellow (watch)
            (0.66, 244, 109,  67),   # orange (warning)
            (1.00, 165,   0,  38),   # red (alert)
        ],
    },
    "classification": {
        "vmin": 0,
        "vmax": 5,
        "stops": [
            (0.00, 200, 200, 200),   # unclassified (grey)
            (0.20,  30, 100, 200),   # water (blue)
            (0.40, 200,  50,  50),   # built-up (red)
            (0.60, 210, 180, 120),   # bare land (tan)
            (0.80, 230, 210,  80),   # cropland (gold)
            (1.00,  20, 120,  50),   # vegetation (green)
        ],
    },
}


def apply_colormap(
    data: np.ndarray,
    colormap_name: str,
    alpha: int = 180,
) -> np.ndarray:
    """Map a 2D float array to an RGBA image using a named colour ramp.

    Parameters
    ----------
    data : ndarray, float32 (H, W)
    colormap_name : str
        Key in COLORMAPS dict.
    alpha : int
        Base alpha for valid pixels (0-255).

    Returns
    -------
    ndarray, uint8, shape (H, W, 4) — RGBA image.
    """
    cmap = COLORMAPS[colormap_name]
    vmin, vmax = cmap["vmin"], cmap["vmax"]
    stops = cmap["stops"]

    normalized = np.clip((data - vmin) / (vmax - vmin + 1e-10), 0, 1)

    positions = np.array([s[0] for s in stops])
    r_stops = np.array([s[1] for s in stops], dtype=np.float32)
    g_stops = np.array([s[2] for s in stops], dtype=np.float32)
    b_stops = np.array([s[3] for s in stops], dtype=np.float32)

    # Fill NaN values with 0 prior to uint8 casting to prevent runtime warnings
    r = np.nan_to_num(np.interp(normalized, positions, r_stops), nan=0.0).astype(np.uint8)
    g = np.nan_to_num(np.interp(normalized, positions, g_stops), nan=0.0).astype(np.uint8)
    b = np.nan_to_num(np.interp(normalized, positions, b_stops), nan=0.0).astype(np.uint8)
    a = np.full_like(r, alpha, dtype=np.uint8)

    # NoData pixels are fully transparent
    nodata_mask = np.isnan(data)
    a[nodata_mask] = 0

    return np.stack([r, g, b, a], axis=-1)


def render_to_png_base64(
    data: np.ndarray,
    colormap_name: str,
    alpha: int = 180,
) -> str:
    """Render a 2D array to a base64-encoded PNG data URL.

    Returns
    -------
    str
        A data URL: "data:image/png;base64,..."
    """
    rgba = apply_colormap(data, colormap_name, alpha)
    img = Image.fromarray(rgba, mode="RGBA")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    b64 = base64.b64encode(buffer.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def get_legend_info(colormap_name: str) -> dict:
    """Return legend metadata for a given colour ramp.

    Returns
    -------
    dict with keys: vmin, vmax, stops (list of {position, color}).
    """
    cmap = COLORMAPS[colormap_name]
    return {
        "vmin": cmap["vmin"],
        "vmax": cmap["vmax"],
        "stops": [
            {
                "position": s[0],
                "color": f"rgb({s[1]},{s[2]},{s[3]})",
            }
            for s in cmap["stops"]
        ],
    }
