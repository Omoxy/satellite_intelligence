# Security review

**Review date:** 2026-10-05
**Scope:** Current uncommitted changes in this repository, including tracked diffs, untracked files, and relevant ignore rules.
**Overall verdict:** FAIL

This review was read-only. No application or configuration changes were made as part of the review. Findings describe the reviewed working tree at the time of review.

## Findings

### HIGH — Anonymous proxy requests can use the backend access key

**Location:** `frontend/netlify/functions/backend-proxy.mjs:53-55`
**Confidence:** 10/10

The public `/api/*` rewrite in `netlify.toml` sends requests through the Netlify function. The function injects the server-side `API_ACCESS_KEY` for protected write routes without authenticating the caller. The backend accepts that key, so an anonymous internet caller can reach write operations such as creating AOIs or analyses and deleting custom AOIs. The shared key proves that the proxy has the key; it does not establish the identity or permissions of the caller.

**Required change before production use:** Do not inject the shared backend key for anonymous write requests. Either limit the public proxy to explicitly allowed read-only operations or require real caller authentication and enforce authorization for each operation and AOI before forwarding the request. Do not expose the shared backend key to frontend code.

### LOW — Local deployment state is not ignored

**Location:** `.gitignore:67-68`
**Confidence:** 9/10

The ignore rules cover environment files, credential/key patterns, build outputs, caches, and logs, but do not cover local Netlify and Vercel state directories. No such deployment-state directories were present among the reviewed changes; this is a preventive coverage gap, not evidence of a leaked credential.

**Required change:** Add ignore rules for `.netlify/` and `.vercel/`, following the repository's ignore-rule conventions. Keep the intentional `netlify.toml` and environment example files trackable.

## Category results

| Category | Result | Notes |
|---|---|---|
| Hardcoded secrets / exposed credentials | PASS | No actual credentials were found in the reviewed changes. |
| Insecure API proxying | FAIL | The public proxy injects a backend key for unauthenticated writes. |
| Authentication / authorization | FAIL | Proxy callers can use the shared backend key without caller authentication or authorization. |
| CORS | PASS | The reviewed backend configuration uses explicit origins. CORS is not an authorization control and does not address the proxy finding. |
| Unsafe environment-variable usage | PASS | No unsafe environment-variable source was identified in the reviewed changes. |
| Frontend secret exposure | PASS | The backend access key is not exposed as a frontend variable. The CARTO map key is client-visible for map tiles, not backend authentication. |
| Ignore coverage | FAIL | Local `.netlify/` and `.vercel/` state directories are not ignored; the other reviewed categories are covered. |
