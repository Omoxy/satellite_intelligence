# Render Backend Deployment

## Render Web Service

Create a native Python web service from this repository with:

- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`
- **Python Runtime:** Python 3.14 (the repository documents Python 3.10+ and tests on 3.14)

Do not add `--reload`. Render supplies `PORT`; the application binds to `0.0.0.0` by default.

Set these environment variables in Render:

| Name | Value/handling |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `PYTHON_VERSION` | `3.14.0` |
| `API_ACCESS_KEY` | Generate a unique random secret of at least 32 characters; keep it secret. |
| `CORS_ORIGINS` | `https://satelliteintelligence.netlify.app` |
| `DATABASE_PATH` | `/var/data/satellite_intelligence.db` when using the persistent disk below |
| `RASTER_CACHE_DIR` | `/var/data/rasters` when using the persistent disk below |
| `DATA_MODE` | `demo` (default; optional) |
| `LOG_LEVEL` | `INFO` (default; optional) |

Do not set `PORT` manually. `HOST` defaults to `0.0.0.0`. Sentinel Hub is optional in demo mode. For live mode, set `SENTINEL_HUB_CLIENT_ID` and `SENTINEL_HUB_CLIENT_SECRET` as Render secrets; never put their values in the repository. `SENTINEL_HUB_INSTANCE_ID` is currently read by configuration but is not required by the current request code.

## Persistent Storage

The application creates a missing SQLite database and initializes its schema during startup. Without persistent storage, Render's default filesystem is ephemeral. Restart or redeploy can discard custom AOIs, analysis runs and results, generated `custom_aoi_*.tif` rasters, and live Sentinel Hub raster caches. The curated study-area GeoTIFFs and `study_areas.json` remain part of the deployed source tree and are not written to the disk mount.

A Render persistent disk is recommended for retaining database state and generated/live raster caches. Mount it at `/var/data`, then use the `DATABASE_PATH` and `RASTER_CACHE_DIR` values above. No PostgreSQL or Redis service is required for the current single-instance architecture. The in-memory rate limiter is per process; keep one service instance for a shared quota, since multiple instances have independent counters.

## Netlify Proxy

The frontend keeps relative `/api` and `/health` requests when `VITE_API_URL` is unset. Netlify rewrites those same-origin paths to `frontend/netlify/functions/backend-proxy.mjs`. Configure these Netlify environment variables for the Functions runtime:

| Name | Value/handling |
| --- | --- |
| `BACKEND_URL` | The actual HTTPS origin assigned by Render, without a path suffix. Set only after the service exists. |
| `API_ACCESS_KEY` | The same generated secret configured in Render; server-side only, not a `VITE_` variable. The proxy uses it only to sign the Netlify client IP for backend rate limiting. |

Leave `VITE_API_URL` unset/empty when using the Netlify proxy. If set, the browser calls that API origin directly; protected write/analysis operations intentionally do not send the shared key from browser code. `VITE_CARTO_API_KEY` is client-visible and is unrelated to backend authentication.

## Public API Controls

There is no user login or per-user authorization system. The Netlify proxy is deliberately read-only: it forwards only `GET /health`, `GET /api/areas`, `GET /api/areas/{area_id}`, `GET /api/analysis/{analysis_id}`, and `GET /api/location` requests. It rejects AOI creation/deletion and analysis execution with HTTP 403, even if a caller supplies `X-API-Key` or `Authorization` headers. Other paths and methods are not forwarded. Consequently, frontend create/delete/analysis actions are unavailable until real user authentication and authorization are implemented.

The backend remains authoritative. `POST /api/areas`, `DELETE /api/areas/{area_id}`, and `POST /api/analysis` require the server-side `X-API-Key`; production startup fails if `API_ACCESS_KEY` is missing or shorter than 32 characters. The key is a shared server-to-server credential, not user authentication: do not put it in frontend code, a `VITE_` variable, or browser storage. Local loopback development remains available without a key; remote writes still require one.

The Render service URL is publicly routable unless you separately configure provider-level ingress restrictions. Direct callers can bypass the Netlify read-only proxy, but cannot perform protected writes without the server-side key. Keep Render's key secret and restrict backend ingress to trusted infrastructure if your deployment requirements demand that reads also pass through Netlify. Confirm that the selected Render/Netlify plans support compatible private networking or ingress controls; CORS is not an access-control substitute. Do not add a public write path until it validates genuine caller identity and operation-level authorization.

The Netlify function signs the Netlify-provided client IP with the shared secret so backend quotas remain per client without trusting caller-supplied forwarding headers. Requests to `/api/*` are rate-limited per client using `RATE_LIMIT_PER_MINUTE`; `POST /api/analysis` has a separate quota of one fifth that value (minimum one request per minute). POST/PUT/PATCH bodies are limited by `MAX_REQUEST_SIZE_MB`, before route processing. These controls are process-local, not a substitute for an edge WAF or multi-instance distributed quota.

AOI geometry/type/topology and maximum-area validation remain enabled. CORS allows the configured exact origins; it is not used as authorization. `/health` remains public and performs only a SQLite connectivity check, not satellite analysis.
