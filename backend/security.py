"""Lightweight request protections for public deployment."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
import threading
import time

from fastapi import Request
from fastapi.responses import JSONResponse

import config


class FixedWindowRateLimiter:
    """Process-local per-client quotas for a single service instance."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[tuple[str, str, int], int] = {}

    def allow(self, bucket: str, client: str, limit: int) -> bool:
        window = int(time.monotonic() // 60)
        key = (bucket, client, window)
        with self._lock:
            self._counts = {entry: count for entry, count in self._counts.items() if entry[2] >= window - 1}
            count = self._counts.get(key, 0)
            if count >= limit:
                return False
            self._counts[key] = count + 1
            return True

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


rate_limiter = FixedWindowRateLimiter()


def client_identifier(request: Request) -> str:
    """Use the Netlify client IP only when authenticated by the shared secret."""
    forwarded_ip = request.headers.get("x-proxy-client-ip", "")
    timestamp = request.headers.get("x-proxy-timestamp", "")
    signature = request.headers.get("x-proxy-signature", "")
    if config.API_ACCESS_KEY and forwarded_ip and timestamp and signature:
        try:
            canonical_ip = str(ipaddress.ip_address(forwarded_ip))
            issued_at = int(timestamp)
        except ValueError:
            pass
        else:
            payload = f"{issued_at}:{forwarded_ip}".encode()
            expected = hmac.new(config.API_ACCESS_KEY.encode(), payload, hashlib.sha256).hexdigest()
            if abs(time.time() - issued_at) <= 60 and hmac.compare_digest(signature, expected):
                return canonical_ip

    return request.client.host if request.client else "unknown"


def is_protected_write(request: Request) -> bool:
    path = request.url.path
    return (
        (request.method == "POST" and path in {"/api/areas", "/api/analysis"})
        or (request.method == "DELETE" and path.startswith("/api/areas/"))
    )


def authorize_write(request: Request) -> JSONResponse | None:
    """Require a constant-time checked shared key for writes and analysis."""
    if not is_protected_write(request):
        return None

    if not config.API_ACCESS_KEY:
        client_host = request.client.host if request.client else ""
        if config.ENVIRONMENT != "production" and client_host in {"127.0.0.1", "::1", "testclient"}:
            return None
        return JSONResponse(status_code=503, content={"detail": "API access is not configured."})

    supplied_key = request.headers.get("x-api-key", "")
    if not secrets.compare_digest(supplied_key, config.API_ACCESS_KEY):
        return JSONResponse(
            status_code=401,
            content={"detail": "A valid API access key is required."},
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return None


def enforce_rate_limit(request: Request) -> JSONResponse | None:
    """Limit API traffic and give computational analysis a tighter quota."""
    if not request.url.path.startswith("/api/"):
        return None

    client = client_identifier(request)
    is_analysis = request.method == "POST" and request.url.path == "/api/analysis"
    limit = max(1, config.RATE_LIMIT_PER_MINUTE // 5) if is_analysis else config.RATE_LIMIT_PER_MINUTE
    bucket = "analysis" if is_analysis else "api"
    if rate_limiter.allow(bucket, client, limit):
        return None

    return JSONResponse(
        status_code=429,
        content={"detail": "Request rate limit exceeded. Try again shortly."},
        headers={"Retry-After": "60"},
    )


class RequestSizeLimitMiddleware:
    """Reject oversized mutation bodies before route processing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        max_bytes = config.MAX_REQUEST_SIZE_MB * 1024 * 1024
        content_length = next(
            (value for name, value in scope["headers"] if name.lower() == b"content-length"),
            None,
        )
        if content_length is not None:
            try:
                if int(content_length) > max_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send)
                return

        chunks: list[bytes] = []
        received_bytes = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            received_bytes += len(chunk)
            if received_bytes > max_bytes:
                await self._reject(send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        body_sent = False

        async def replay_body():
            nonlocal body_sent
            if body_sent:
                return {"type": "http.disconnect"}
            body_sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_body, send)

    @staticmethod
    async def _reject(send) -> None:
        body = b'{"detail":"Request body exceeds the configured size limit."}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
            }
        )
        await send({"type": "http.response.body", "body": body})