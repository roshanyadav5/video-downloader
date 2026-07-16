"""
Lightweight in-memory rate limiter. Same scaling caveat as job_manager —
swap for Redis if this ever runs multi-replica. For a single backend
instance this is the right amount of complexity: no extra infrastructure
to run just to throttle abusive clients.
"""
import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit the actual API surface, not health checks.
        if request.url.path.startswith("/api/"):
            settings = get_settings()
            ip = request.client.host if request.client else "unknown"
            now = time.time()
            window_start = now - 60

            recent = [t for t in self._hits[ip] if t > window_start]
            recent.append(now)
            self._hits[ip] = recent

            if len(recent) > settings.rate_limit_requests_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": "Too many requests. Please slow down.",
                        "error_code": "RATE_LIMITED",
                    },
                )

        return await call_next(request)
