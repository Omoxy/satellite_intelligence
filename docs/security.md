# Application Security Review & DevSecOps Posture

## 1. Threat Model & Security Posture

Satellite Intelligence Explorer implements defence-in-depth principles across all architectural tiers:

### 1.1 Secret Management
- **Zero Secrets in Repository:** No API keys, credentials, database passwords, or private keys are stored in source code, comments, or committed files.
- **Strict `.gitignore`:** Excludes all `.env`, `.pem`, `.key`, `service-account*.json`, and credential artifacts.
- **Placeholder Template:** `.env.example` contains only variable keys with blank placeholder values.
- **Client Sanitisation:** No backend secrets are exposed to the browser or embedded into the client-side bundle.

### 1.2 Input Validation & Injection Prevention
- **SQL Injection Prevention:** All database operations utilize strictly parameterised queries through SQLite/SpatiaLite bindings. No raw string interpolation or user input concatenation exists in SQL statements.
- **Geometry Sanitisation:** All GeoJSON payloads are validated against OGC standards using Shapely. Malformed geometries, invalid coordinate hierarchies, and non-polygonal types are rejected with HTTP 422.
- **Resource Denial-of-Service Limits:** AOI areas are bounded with minimum ($1,000\text{ m}^2$) and maximum ($10,000\text{ km}^2$) thresholds to prevent algorithmic CPU or memory exhaustion.

### 1.3 HTTP & API Hardening
- **Explicit CORS Configuration:** Restricts origins to configured domain list (default `http://localhost:5173`); wildcards (`*`) are disallowed on state-changing endpoints.
- **Security Headers:** Middleware automatically enforces:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: geolocation=(), camera=(), microphone=()`
- **Error Obfuscation:** RFC 7807 compliant error responses return safe problem details to clients. Internal stack traces, database schema specifics, and server file paths are logged server-side only and never leaked to users.
