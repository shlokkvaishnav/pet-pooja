"""
rate_limit.py — Simple In-Process Rate Limiter
=================================================
Token-bucket per client IP, scoped by route group.
No external dependencies (no Redis needed).

Env vars:
  RATE_LIMIT_ENABLED — "true" to enforce (default: true)
  RATE_LIMIT_VOICE_RPM — requests/min for /api/voice/* (default: 20)
  RATE_LIMIT_REVENUE_RPM — requests/min for /api/revenue/* (default: 60)
  RATE_LIMIT_DEFAULT_RPM — requests/min for other routes (default: 120)
"""

import os
import time
import logging
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request, HTTPException, status

logger = logging.getLogger("petpooja.rate_limit")


def _env_int(name: str, default: int, *, min_value: int = 1) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid %s=%r; using default %d", name, raw, default)
        return default
    if value < min_value:
        logger.warning("%s must be >= %d; using default %d", name, min_value, default)
        return default
    return value


ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes")
_VOICE_RPM = _env_int("RATE_LIMIT_VOICE_RPM", 20)
_REVENUE_RPM = _env_int("RATE_LIMIT_REVENUE_RPM", 200)
_DEFAULT_RPM = _env_int("RATE_LIMIT_DEFAULT_RPM", 120)

# Sliding window size in seconds
_WINDOW = 60


class _RateLimiter:
    """Per-key sliding-window counter with automatic cleanup."""

    def __init__(self):
        self._lock = Lock()
        # key -> deque of timestamps (O(1) eviction from left)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._last_cleanup = time.time()

    def check(self, key: str, max_requests: int) -> bool:
        """Return True if allowed, False if rate-limited."""
        now = time.time()
        cutoff = now - _WINDOW

        with self._lock:
            # Periodic cleanup of stale keys (every 60s)
            if now - self._last_cleanup > _WINDOW:
                stale = [k for k, v in self._hits.items() if not v or v[-1] < cutoff]
                for k in stale:
                    del self._hits[k]
                self._last_cleanup = now

            timestamps = self._hits[key]
            # Remove expired timestamps
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                return False

            timestamps.append(now)
            return True


_limiter = _RateLimiter()


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind a proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_limit_for_path(path: str) -> int:
    """Return the rate limit (RPM) for given path."""
    if path.startswith("/api/voice"):
        return _VOICE_RPM
    if path.startswith("/api/revenue"):
        return _REVENUE_RPM
    return _DEFAULT_RPM


async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware — check rate limit before processing.
    Keyed by (client_ip, route_group).
    """
    if not ENABLED:
        return await call_next(request)

    # Skip health checks
    if request.url.path in ("/health", "/api/health"):
        return await call_next(request)

    client_ip = _get_client_ip(request)
    rpm = _get_limit_for_path(request.url.path)
    path_parts = request.url.path.split("/")
    route_group = path_parts[2] if len(path_parts) > 2 else "root"
    key = f"{client_ip}:{route_group}"

    if not _limiter.check(key, rpm):
        logger.warning("Rate limit exceeded: %s on %s (%d RPM)", client_ip, request.url.path, rpm)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {rpm} requests per minute for this endpoint.",
        )

    return await call_next(request)
