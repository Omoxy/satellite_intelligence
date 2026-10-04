# System Architecture: Satellite Intelligence Explorer

## 1. Overview

Satellite Intelligence Explorer is an interactive Earth Observation analysis and environmental anomaly monitoring platform engineered for geospatial professionals, agronomists, and remote sensing analysts.

The platform follows a decoupled, service-oriented GIS architecture:

* Client Layer: Map-first React 18 and TypeScript Single Page Application powered by Leaflet.
* API and Gateway Layer: Python 3.14 and FastAPI asynchronous REST service.
* Geospatial Processing Engine: Scientific stack utilizing Rasterio, NumPy, Shapely, PyProj, and Pillow computing band math, zonal statistics, and anomaly detection.
* Spatial Persistence Layer: Embedded spatial database structured with an OGC and PostGIS compatible relational schema.
* Data Acquisition Layer: Multi-spectral GeoTIFF surface reflectance pipeline operating with deterministic physical synthesis for portfolio demonstration.

---

## 2. End-to-End System Pipeline

The data flow executes genuine scientific computation across every stage:

```text
Deterministic raster input (Multi-band GeoTIFF)
        ↓
Rasterio reads raster from disk
        ↓
Raster metadata, CRS, and NoData validation
        ↓
AOI transformed into raster CRS
        ↓
Raster clipped and windowed to AOI via rasterio.mask
        ↓
Actual spectral bands extracted (Blue, Green, Red, NIR, SWIR)
        ↓
NumPy performs spectral index calculation
        ↓
Actual NDVI, NDMI, NDWI, NDBI raster arrays
        ↓
Actual zonal statistics and distribution histograms
        ↓
Actual multi-temporal change detection
        ↓
Actual statistical baseline anomaly calculation
        ↓
Backend FastAPI response
        ↓
React Web GIS frontend
        ↓
Interactive Leaflet map, charts, inspector, and summary
        ↓
Vector PDF report generation via jsPDF
```

---

## 3. Spatial Database Architecture and Portability

This project uses SpatiaLite as an embedded spatial database to keep the portfolio application self-contained and easy to run locally. SpatiaLite provides geometry storage, spatial functions, and spatial indexing without requiring a separate database server. It was selected for portability rather than because it is interchangeable with PostgreSQL and PostGIS in every operational respect. A production multi-user deployment could migrate the schema and spatial query patterns to PostgreSQL and PostGIS, which provides a broader enterprise database ecosystem and operational capabilities.

### Relational Schema Tables:
* `areas_of_interest`: ID, name, GeoJSON geometry, geodesic area, centroid, bounding box coordinates, and predefined flag.
* `analysis_runs`: ID, foreign key to AOI, observation window, data source, cloud contamination percentage, execution timestamps.
* `indicator_results`: Computed spatial statistics (mean, min, max, standard deviation), histogram bins, and raster PNG overlay strings.
* `change_results`: Absolute change, percentage shifts, and spatial gain, stable, reduction breakdowns.
* `timeseries`: Multi-date historical observations with quality tracking.
* `anomalies`: Deviation sigma, threshold, classification (`normal`, `watch`, `warning`, `alert`), and descriptive text.
* `classification_results`: Rule-based land-cover classes and area percentages.

---

## 4. Geospatial Processing Engine Specifications

### 4.1 Rasterio GeoTIFF Management
The engine reads genuine multi-band GeoTIFF files located in `backend/data/rasters/`. Each GeoTIFF contains 5 spectral bands:
* Band 1: Blue (B2, ~490 nm)
* Band 2: Green (B3, ~560 nm)
* Band 3: Red (B4, ~665 nm)
* Band 4: NIR (B8, ~842 nm)
* Band 5: SWIR-1 (B11, ~1610 nm)

CRS is validated as EPSG:4326. NoData values (-9999.0) are converted to float32 NaN values prior to index computation.

### 4.2 Spatial Clipping and Windowing
When an AOI is submitted, `raster_engine.load_and_clip_raster` invokes `rasterio.mask.mask` with `crop=True` and `all_touched=True`. The raster is clipped to the exact bounding polygon, and zonal statistics are calculated exclusively from the intersecting pixels.

### 4.3 Point Location Inspector
Probing any coordinate executes `rasterio.windows` and `src.index(lng, lat)` to extract pixel band reflectance directly from the underlying GeoTIFF raster.
