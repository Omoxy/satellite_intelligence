# Satellite Intelligence Explorer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB.svg)](https://www.python.org)
[![Tests](https://img.shields.io/badge/Tests-35%20passed-success.svg)](./backend/tests)

An interactive Earth Observation (EO) analysis and environmental anomaly monitoring platform engineered for geospatial developers, remote-sensing specialists, and agricultural decision-makers.

Designed around European Space Agency (ESA) Copernicus Sentinel-2 MSI multi-spectral surface reflectance, the platform provides automated computation of spectral vegetation, moisture, water, and built-up indices, statistical anomaly detection against multi-season historical baselines, and multi-temporal change mapping across demonstration study areas in Kenya.

---

## 1. Problem & Agricultural Context

Smallholder agricultural systems and ecological corridors across sub-Saharan Africa face rapid environmental volatility, including erratic seasonal rainfall, drought-induced canopy stress, and uncontrolled land-use transitions.

Traditional remote-sensing toolchains are frequently hindered by:
1. High barriers to entry for non-technical field officers requiring specialized GIS desktop software (e.g., QGIS, ArcGIS).
2. Opaque or fabricated "AI" claims that present statistical proxies as absolute ground truth without field verification caveats.
3. Heavy client-side raster processing that crashes browser viewports on resource-constrained networks.

**Satellite Intelligence Explorer** addresses these challenges by decoupling heavy raster band math to an asynchronous Python scientific engine, streaming lightweight RGBA PNG overlays to an interactive Leaflet web client, and enforcing responsible biophysical reporting.

---

## 2. Key Features

- **Interactive Web GIS Client:** Map-first viewport powered by Leaflet with OpenStreetMap and optional CARTO Dark Matter basemaps, plus smooth vector bounding box synchronization.
- **Multi-Spectral Band Math:** Vectorised computation of NDVI, NDMI, NDWI, and NDBI from Sentinel-2 MSI Level-2A surface reflectance.
- **Reference Kenyan Study Areas:** Pre-seeded geographic extents across 5 contrasting biomes:
  - **Nairobi:** Urban-rural gradient with dense built-up fabric and urban parklands.
  - **Nakuru:** Great Rift Valley lake basin featuring alkaline wetland ecology and mixed crop transitions.
  - **Murang'a:** Central highland tea and coffee plantation slopes with steep terrain.
  - **Siaya:** Western Lake Victoria basin with smallholder mixed cropping and seasonal wetlands.
  - **Elgeyo-Marakwet:** Dramatic Rift escarpment gradient (900m valley floor to 3,000m Cherangani montane forest).
- **Zonal Statistics & Histograms:** Calculation of spatial mean, min, max, standard deviation, and 20-bin pixel distribution histograms per indicator.
- **Multi-Temporal Change Detection:** Epoch-to-epoch differential analysis ($T_2 - T_1$) evaluating absolute change, percentage shifts, and spatial gain/stable/reduction classifications.
- **Statistical Anomaly Detection:** Z-score departure assessment against historical multi-season baselines with automated alert classification (`NORMAL`, `WATCH`, `WARNING`, `ALERT`).
- **Rule-Based Land Cover Classification:** Scientifically transparent threshold classification into Water, Built-up, Bare Land, Cropland, and Dense Vegetation.
- **Interactive Point Probe Inspector:** Click anywhere on the map to sample real-time spectral values, historical baseline comparisons, and biophysical interpretations.
- **Dossier Export:** Client-side vector PDF and raw JSON report generation via `jsPDF`.

---

## 3. System Architecture

The application adopts a decoupled service-oriented architecture:

```mermaid
graph TD
    User([Geospatial Analyst / Recruiter]) -->|Interacts with UI| WebGIS[React + Leaflet GIS Client]

    subgraph Client Application [Frontend: React 18 + TypeScript + Leaflet]
        WebGIS --> MapView[Interactive Map Viewport]
        WebGIS --> LayerCtrl[Layer & Colormap Controls]
        WebGIS --> AOICtrl[AOI & Parameter Panel]
        WebGIS --> ResultsDashboard[Zonal Stats & Histogram]
        WebGIS --> TimeSeries[Temporal Trajectory Chart]
        WebGIS --> ProbeInspector[Point Probe Inspector]
        WebGIS --> PDFExport[jsPDF Report Generator]
    end

    WebGIS -->|HTTP REST / JSON| APIGateway[FastAPI Application Gateway]

    subgraph Backend Service [FastAPI + Scientific Engine]
        APIGateway --> SecurityMW[Security Headers & CORS Middleware]
        SecurityMW --> Routers[API Route Dispatcher]

        Routers --> AreaRouter[/api/areas]
        Routers --> AnalysisRouter[/api/analysis]
        Routers --> LocationRouter[/api/location]

        AnalysisRouter --> GeomValidator[OGC Geometry Validator - Shapely]
        AnalysisRouter --> BandAcquisition[Surface Reflectance Acquisition]

        subgraph Scientific Processing Pipeline
            BandAcquisition --> SpectralEngine[Spectral Index Engine: NDVI / NDMI / NDWI / NDBI]
            SpectralEngine --> ZonalStats[Zonal Statistics & 20-bin Histogram]
            SpectralEngine --> ChangeDetector[Multi-temporal Change Detection]
            SpectralEngine --> AnomalyDetector[Z-Score Baseline Anomaly Classifier]
            SpectralEngine --> Classifier[Rule-based Land Cover Classifier]
            SpectralEngine --> RasterRenderer[RGBA Colormap PNG Renderer]
        end
    end

    subgraph Persistence Layer [Relational Spatial DB]
        Routers --> DB[(SQLite Spatial DB)]
        DB --> TblAOI[areas_of_interest]
        DB --> TblRuns[analysis_runs]
        DB --> TblInd[indicator_results]
        DB --> TblChg[change_results]
        DB --> TblTS[timeseries]
        DB --> TblAnom[anomalies]
        DB --> TblClass[classification_results]
    end
```

---

## 4. Remote Sensing Methodology & Formulas

### 4.1 Spectral Indices

All indicators adhere to the normalised difference ratio:

$$\text{Index} = \frac{\rho_A - \rho_B}{\rho_A + \rho_B}$$

| Indicator | Sentinel-2 Bands | Wavelengths | Interpretation Range | Literature Reference |
|---|---|---|---|---|
| **NDVI** | $(B8 - B4) / (B8 + B4)$ | 842nm / 665nm | $<0.1$ Bare; $0.2-0.4$ Cropland; $>0.6$ Dense Canopy | Rouse et al. (1974) |
| **NDMI** | $(B8 - B11) / (B8 + B11)$ | 842nm / 1610nm | $<-0.1$ Severe Stress; $0.0-0.2$ Normal; $>0.4$ High Water | Gao (1996) |
| **NDWI** | $(B3 - B8) / (B3 + B8)$ | 560nm / 842nm | $<0.0$ Terrestrial; $>0.2$ Open Water Surface | McFeeters (1996) |
| **NDBI** | $(B11 - B8) / (B11 + B8)$ | 1610nm / 842nm | $<-0.2$ Vegetation; $>0.1$ Urban Fabric / Built-up | Zha et al. (2003) |

### 4.2 Multi-Temporal Change Detection

Evaluates spatial difference across two dates ($T_1$ and $T_2$):
- **Absolute Shift:** $\Delta \text{Index} = \text{Index}_{T2} - \text{Index}_{T1}$
- **Percentage Shift:** $\% \Delta = \frac{\Delta \text{Index}}{|\text{Index}_{T1}|} \times 100$
- **Classification:** Categorised as *Gain* ($>+0.05$), *Reduction* ($<-0.05$), or *Stable* ($[-0.05, +0.05]$).

### 4.3 Statistical Anomaly Detection

Computed using pixel-level departure from multi-epoch baselines:

$$z = \frac{\mu_{\text{current}} - \mu_{\text{baseline}}}{\sigma_{\text{baseline}}}$$

- **NORMAL:** $|z| < 1.0\sigma$
- **WATCH:** $1.0\sigma \le |z| < 1.5\sigma$
- **WARNING:** $1.5\sigma \le |z| < 2.0\sigma$
- **ALERT:** $|z| \ge 2.0\sigma$

---

## 5. Technology Stack

### Frontend
- **Framework:** React 18 + TypeScript (Strict Mode)
- **Bundler:** Vite 6
- **Web GIS:** Leaflet 1.9.4 + OpenStreetMap and CARTO Dark Matter basemaps
- **Icons:** Lucide React
- **Export Engine:** jsPDF (Client-side vector report synthesis)
- **Styling:** Custom CSS design system (Forest Green `#1B4332`, Gold `#F4A261`, Dark `#0D1B2A`)

### Backend
- **Framework:** Python 3.14 + FastAPI
- **Web Server:** Uvicorn (ASGI)
- **Validation:** Pydantic v2
- **Raster Processing:** Rasterio (Multi-band GeoTIFF access, metadata/CRS validation, windowed spatial masking via `rasterio.mask`)
- **Vector & Geometry:** Shapely (OGC validity, polygon buffers, geodesic metric approximation)
- **Array Math & Statistics:** NumPy (Vectorised float32 band math, NaN safety)
- **Raster Rendering:** Pillow (Piecewise linear RGBA PNG generation)
- **Database:** SpatiaLite / SQLite embedded spatial database with PostGIS-compatible relational schema

---

## 6. Project Structure

```
satellite-intelligence-explorer/
├── README.md                          # Comprehensive project documentation
├── LICENSE                            # MIT License
├── .gitignore                         # Security-hardened gitignore
├── .env.example                       # Environment configuration template
│
├── docs/                              # Technical architecture & methodology
│   ├── architecture.md                # System diagrams, pipeline flows, and SpatiaLite vs PostGIS
│   ├── methodology.md                 # Remote sensing formulas & references
│   ├── data-sources.md                # Sentinel-2 specifications & data provenance
│   ├── security.md                    # Threat model & DevSecOps controls
│   └── testing.md                     # QA test matrix and execution results
│
├── backend/                           # Python FastAPI Geospatial Service
│   ├── requirements.txt               # Locked dependencies
│   ├── main.py                        # Application entrypoint & middleware
│   ├── config.py                      # Environment settings loader
│   ├── database.py                    # SpatiaLite/SQLite relational schema & connection lifecycle
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py                 # Pydantic request/response schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── areas.py                   # /api/areas CRUD & Kenyan AOI seeding
│   │   ├── analysis.py                # /api/analysis EO processing pipeline
│   │   └── location.py                # /api/location point probe inspector
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── raster_engine.py           # Rasterio GeoTIFF clipping, windowing & point probe
│   │   ├── spectral.py                # NDVI, NDMI, NDWI, NDBI band math
│   │   ├── change_detection.py        # Multi-temporal epoch differential math
│   │   ├── anomaly.py                 # Baseline z-score anomaly classifier
│   │   ├── classification.py          # Rule-based land-cover decision tree
│   │   ├── geometry.py                # Shapely OGC validation & metric bounds
│   │   ├── statistics.py              # Zonal statistics & 20-bin histogram
│   │   ├── rendering.py               # Scientific RGBA colormap raster generator
│   │   └── demo_data.py               # Deterministic physical synthesis generator
│   ├── data/
│   │   ├── study_areas.json           # GeoJSON definitions for 5 Kenyan AOIs
│   │   ├── satellite_intelligence.db  # SpatiaLite / SQLite database instance
│   │   └── rasters/                   # Sensed multi-band GeoTIFF rasters
│   └── tests/
│       ├── __init__.py
│       ├── test_spectral.py           # Spectral index unit tests
│       ├── test_change_detection.py   # Change detection unit tests
│       ├── test_anomaly.py            # Baseline anomaly tests
│       ├── test_geometry.py           # Geometry validation tests
│       ├── test_api.py                # API integration test suite
│       ├── test_security.py           # Security & injection test suite
│       └── test_forensic_pipeline.py  # 10 mandated forensic audit scenarios
│
├── frontend/                          # React 18 + TypeScript Web GIS Client
│   ├── package.json                   # Locked dependencies
│   ├── tsconfig.json                  # Strict TypeScript configuration
│   ├── vite.config.ts                 # Vite bundler configuration
│   ├── index.html                     # Application HTML template
│   └── src/
│       ├── main.tsx                   # React DOM bootstrap
│       ├── App.tsx                    # Root GIS dashboard layout
│       ├── index.css                  # Cartographic design system
│       ├── types/
│       │   └── index.ts               # Shared TypeScript data contracts
│       ├── api/
│       │   └── client.ts              # Typed API communication client
│       └── components/
│           ├── Map/
│           │   ├── MapView.tsx        # Leaflet interactive map viewport
│           │   └── LayerControl.tsx   # Colormap legend & layer opacity controls
│           ├── Analysis/
│           │   ├── AnalysisPanel.tsx  # AOI selection & temporal parameter controls
│           │   ├── ResultsView.tsx    # Zonal statistics, change, and anomaly cards
│           │   └── TemporalChart.tsx  # SVG time-series trajectory with envelope
│           ├── Inspector/
│           │   └── LocationInspector.tsx # Point coordinate probe inspector
│           └── Export/
│               └── ExportModal.tsx    # jsPDF vector report generator
│
└── scripts/
    ├── build_demo_rasters.py          # Multi-band GeoTIFF raster generator
    └── generate_demo_data.py          # CLI tool for inspecting synthetic bands
```

---

## 7. Installation & Running Locally

### Prerequisites
- **Python 3.10+** (tested on Python 3.14)
- **Node.js 18+** (tested on Node.js 24)

### Step 1: Clone Repository
```bash
git clone https://github.com/Omoxy/MoxEs.git satellite-intelligence-explorer
cd satellite-intelligence-explorer
```

### Step 2: Configure Environment
```bash
cp .env.example .env
```
*(The default configuration runs out-of-the-box in deterministic demonstration mode without requiring external API keys).*

### Step 3: Run Backend Service
```bash
cd backend
pip install -r requirements.txt
python main.py
```
*The FastAPI backend will initialise the SQLite database, seed the 5 Kenyan study areas, and listen on `http://localhost:8000` (API documentation available at `http://localhost:8000/api/docs`).*

### Step 4: Run Frontend GIS Client (in a separate terminal)
```bash
cd frontend
npm install
npm run dev
```
*Access the interactive GIS workstation at `http://localhost:5173`.*

---

## 8. Operating Modes & Demonstration Integrity

To ensure that recruiters and GIS engineers can evaluate the platform from a clean clone without paid subscriptions:
- **Default Mode:** `DATA_MODE=demo`
- **Methodology:** Surface reflectance is produced via deterministic physical landscape synthesis based on Kenyan topography seeds and bimodal seasonal curves, stored as multi-band GeoTIFF rasters and processed via Rasterio.
- **Ethical Labeling:** The application explicitly badges this as **DEMO MODE (SYNTHESIS)** in the UI and exported reports. Results are never falsely claimed to be live unverified ground truth.

> **DEMONSTRATION DATA**
>
> This project uses deterministic synthetic reflectance data to demonstrate the Earth-observation processing pipeline. The remote-sensing calculations are real, but the demonstration raster values are not measurements from current satellite acquisitions.

---

## 9. Automated Testing & Verification

Execute the complete 35-case test suite:

```bash
cd backend
python -m pytest tests/ -v
```

```
============================== 35 passed in 7.86s ==============================
tests/test_spectral.py ......................... [100%]
tests/test_change_detection.py ................ [100%]
tests/test_anomaly.py .......................... [100%]
tests/test_geometry.py ......................... [100%]
tests/test_api.py .............................. [100%]
tests/test_security.py ......................... [100%]
tests/test_forensic_pipeline.py ................ [100%]
```

---

## 10. Security & Threat Mitigation

- **No Committed Secrets:** Repository strictly checked; all keys, tokens, and credentials are kept out of Git via `.gitignore`.
- **SQL Injection Defense:** All SQLite queries execute through parameterised bindings; no dynamic SQL string concatenation.
- **Strict OGC Geometry Validation:** Malformed or self-intersecting geometries are validated and buffered using Shapely before database storage.
- **CORS & Security Headers:** Explicit origin binding with `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` enforced on all responses.

---

## 11. Spatial Database Architecture & Portability

This project uses SpatiaLite as an embedded spatial database to keep the portfolio application self-contained and easy to run locally. SpatiaLite provides geometry storage, spatial functions, and spatial indexing without requiring a separate database server. It was selected for portability rather than because it is interchangeable with PostgreSQL/PostGIS in every operational respect. A production multi-user deployment could migrate the schema and spatial query patterns to PostgreSQL/PostGIS, which provides a broader enterprise database ecosystem and operational capabilities.

- **Raster Tiling:** Currently renders custom PNG overlays scaled to AOI bounds. Integration of Cloud Optimized GeoTIFF (COG) streaming via TiTiler is planned for continental-scale AOIs.
- **Radar Integration:** Future versions will incorporate Sentinel-1 Synthetic Aperture Radar (SAR) VV/VH polarization backscatter for cloud-penetrating moisture tracking.
- **PostGIS Scalability:** The relational schema directly translates to PostGIS DDL; a Docker Compose profile with PostgreSQL 16 + PostGIS 3.4 is prepared for multi-tenant deployments.

---

## 12. License & Attribution

- **Code License:** [MIT License](LICENSE) © 2026 Omoxy.
- **Base Cartography:** Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright); CARTO Dark Matter © [CARTO](https://carto.com/attribution/).
- **Satellite Data Standards:** European Space Agency (ESA) Copernicus Sentinel-2 MSI data specifications.
