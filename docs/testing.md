# Quality Assurance & Testing Dossier

## 1. Test Architecture

The test suite covers unit math, geometry topology, API integration, security controls, and the forensic pipeline audit across 35 automated test cases in `backend/tests/`:

```
backend/tests/
├── test_spectral.py           # NDVI, NDMI, NDWI, NDBI calculations & division-by-zero checks
├── test_change_detection.py   # Absolute & relative change detection, threshold classification
├── test_anomaly.py            # Multi-temporal baseline, z-score deviation, alert thresholds
├── test_geometry.py           # OGC validation, self-intersection repair, area bounds
├── test_api.py                # FastAPI TestClient integration across areas, analysis, probe
├── test_security.py           # SQL injection attempts, CORS, security headers, date validations
└── test_forensic_pipeline.py  # 10 mandated forensic audit scenarios (Nairobi, Nakuru, sub-AOIs, etc.)
```

---

## 2. Test Execution

Execute the full suite using pytest:

```bash
cd backend
python -m pytest tests/ -v
```

### Coverage Thresholds & Results
- **Pass Rate:** 100% (35 / 35 test cases passing).
- **Execution Time:** ~7 seconds.
- **Compiler / Linter Warnings:** Zero.
