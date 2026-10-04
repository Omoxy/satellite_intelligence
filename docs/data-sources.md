# Earth Observation Data Sources & Quality Disclosures

## 1. Primary Data Specifications

Satellite Intelligence Explorer is engineered for optical multi-spectral satellite imagery, natively designed around the European Space Agency (ESA) Copernicus Sentinel-2 constellation:

| Property | Specification |
|---|---|
| **Satellite Constellation** | Sentinel-2A and Sentinel-2B |
| **Sensor** | Multi-Spectral Instrument (MSI) |
| **Product Level** | Level-2A (Bottom-of-Atmosphere / Surface Reflectance) |
| **Coordinate Reference System** | WGS84 (EPSG:4326) / UTM projected grids |
| **Native Spatial Resolution** | 10m (B2, B3, B4, B8), 20m (B5, B6, B7, B8A, B11, B12) |
| **Temporal Resolution** | ~5-day revisit at equatorial latitudes |

---

## 2. Operating Modes: Demonstration vs Live Integration

To allow immediate inspection and testing without mandatory paid API subscriptions, the platform provides two operating modes:

### Mode A: Deterministic Demonstration Synthesis (Default)
- **Status:** Fully functional out-of-the-box (`DATA_MODE=demo`).
- **Mechanism:** Implements physically-constrained synthetic surface reflectance using actual Kenyan geomorphology seeds, bimodal seasonal rainfall curves (March–May long rains, October–December short rains), and realistic cloud contamination patches.
- **Reproducibility:** Two requests for the same geometry and date yield bit-for-bit identical spectral bands and statistical distributions.
- **Transparency:** Clearly badged in the UI as **DEMO MODE (SYNTHESIS)**.

> **DEMONSTRATION DATA**
>
> This project uses deterministic synthetic reflectance data to demonstrate the Earth-observation processing pipeline. The remote-sensing calculations are real, but the demonstration raster values are not measurements from current satellite acquisitions.

### Mode B: Copernicus Data Space Ecosystem / Sentinel Hub (Live)
- **Status:** Integrated via configuration (`DATA_MODE=live`).
- **Authentication:** Configured via `SENTINEL_HUB_CLIENT_ID` and `SENTINEL_HUB_CLIENT_SECRET` in `.env`.
- **API Standard:** OGC WCS (Web Coverage Service) or Sentinel Hub Processing API returning GeoTIFF multi-band arrays.

---

## 3. Data Quality & Limitations

1. **Cloud Contamination:** Optical sensors cannot penetrate cloud cover. Cloud patches are detected via Sentinel-2 Scene Classification (SCL) masks and flagged as NoData.
2. **Atmospheric Correction:** In live mode, Level-2A processing applies Sen2Cor atmospheric radiative transfer correction; slight residual haze or cirrus may affect radiometric fidelity.
3. **Spatial Scale:** 10m–20m pixel resolution cannot resolve individual tree canopies or sub-meter farm plot boundaries.
