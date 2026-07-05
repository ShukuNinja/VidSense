import os
import threading
import time

from fastapi import Depends, HTTPException, Request

from backend.auth import get_current_user
from backend.models import User


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


# Limits (env-overridable). Ingestion is heavy (download + Whisper), so it's the
# tightest; messages are per-minute; auth is per-IP to blunt brute force.
INGEST_LIMIT = _int_env("VIDSENSE_INGEST_PER_HOUR", 10)
INGEST_WINDOW = 3600
MESSAGE_LIMIT = _int_env("VIDSENSE_MSG_PER_MIN", 30)
MESSAGE_WINDOW = 60
AUTH_LIMIT = _int_env("VIDSENSE_AUTH_PER_5MIN", 10)
AUTH_WINDOW = 300


class FixedWindowLimiter:
    """In-memory fixed-window counter. Fine for a single instance; a multi-replica
    deployment would need a shared store (e.g. Redis)."""

    def __init__(self):
        self._hits: dict[str, list] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window: int) -> None:
        now = time.time()
        with self._lock:
            entry = self._hits.get(key)
            if entry is None or now - entry[0] >= window:
                self._hits[key] = [now, 1]
                return
            if entry[1] >= limit:
                retry = int(window - (now - entry[0])) + 1
                raise HTTPException(
                    429,
                    f"Rate limit exceeded. Try again in {retry}s.",
                    headers={"Retry-After": str(retry)},
                )
            entry[1] += 1


_limiter = FixedWindowLimiter()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:  # set by the Caddy proxy
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def ingest_rate_limit(user: User = Depends(get_current_user)) -> User:
    _limiter.check(f"ingest:{user.id}", INGEST_LIMIT, INGEST_WINDOW)
    return user


def message_rate_limit(user: User = Depends(get_current_user)) -> User:
    _limiter.check(f"msg:{user.id}", MESSAGE_LIMIT, MESSAGE_WINDOW)
    return user


def auth_rate_limit(request: Request) -> None:
    _limiter.check(f"auth:{_client_ip(request)}", AUTH_LIMIT, AUTH_WINDOW)
