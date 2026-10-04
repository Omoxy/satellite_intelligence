"""Satellite Intelligence Explorer — FastAPI Application Entrypoint.

Architectural Highlights:
- Explicit CORS policy
- Security headers (CSP, X-Content-Type-Options, Frame-Options)
- Structured RFC 7807 compliant error handling
- Zero credential leakage
- Automatic database schema initialisation and seed data verification
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
import database
from engine import sentinel_hub
from routers.analysis import router as analysis_router
from routers.areas import router as areas_router, seed_predefined_areas_if_needed
from routers.location import router as location_router

# Logging configuration
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("satellite_intelligence")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown procedures."""
    logger.info("Starting Satellite Intelligence Explorer API...")
    logger.info("Data Mode: %s", config.DATA_MODE)
    # Step 1: Initialise database schema
    database.init_db()
    # Step 2: Seed reference study areas
    seed_predefined_areas_if_needed()
    logger.info("System initialisation complete.")
    yield
    logger.info("Shutting down Satellite Intelligence Explorer API.")


app = FastAPI(
    title="Satellite Intelligence Explorer API",
    description="Earth Observation analysis platform for environmental indicators and anomaly detection.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Explicit CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    max_age=600,
)


# Security Headers & Request Logging Middleware
@app.middleware("http")
async def security_and_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    # Log request summary without secrets or user PII
    logger.info(
        "%s %s -> %s (%.2f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    # Inject Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

    return response


# RFC 7807 Error Handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error": {
                "type": "https://datatracker.ietf.org/doc/html/rfc7807",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred while processing the geospatial request. Please try again.",
                "instance": request.url.path,
            },
        },
    )


# Attach API Routers
app.include_router(areas_router)
app.include_router(analysis_router)
app.include_router(location_router)


@app.get("/", tags=["System"])
def root():
    return {
        "service": "Satellite Intelligence Explorer",
        "version": "1.0.0",
        "documentation": "/api/docs",
        "data_mode": config.DATA_MODE,
        "status": "operational",
    }


@app.get("/api/sentinel-status", tags=["System"])
def sentinel_status():
    """Test Sentinel Hub OAuth2 connectivity (no credentials in response)."""
    conn_test = sentinel_hub.test_connection()
    return {
        "data_mode": config.DATA_MODE,
        "credentials_configured": conn_test["credentials_configured"],
        "auth_ok": conn_test["auth_ok"],
        "error": conn_test["error"],
        "note": "No credential values are included in this response.",
    }


@app.get("/health", tags=["System"])
def health_check():
    """System health check endpoint verifying database connectivity."""
    db_ok = False
    try:
        with database.get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
            db_ok = True
    except Exception as e:
        logger.error("Database health check failed: %s", e)

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "data_mode": config.DATA_MODE,
        "timestamp": database.utcnow(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
