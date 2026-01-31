"""
Rate Limiting Middleware
"""

from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests per IP"""

    def __init__(self, app):
        super().__init__(app)
        self.request_counts: Dict[str, Dict[str, Any]] = {}

    def _check_rate_limit(self, ip: str) -> bool:
        """Check if request is within rate limit"""
        now = datetime.now()
        window = timedelta(seconds=settings.rate_limit_window_seconds)
        limit = settings.rate_limit_requests

        if ip not in self.request_counts:
            self.request_counts[ip] = {"count": 1, "reset_time": now + window}
            return True

        record = self.request_counts[ip]

        # Reset if window expired
        if now > record["reset_time"]:
            self.request_counts[ip] = {"count": 1, "reset_time": now + window}
            return True

        # Check if over limit
        if record["count"] >= limit:
            return False

        # Increment count
        record["count"] += 1
        return True

    async def dispatch(self, request: Request, call_next):
        # Get client IP (check for proxy headers)
        client_ip = request.headers.get("x-forwarded-for", "localhost")
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        # Check rate limit
        if not self._check_rate_limit(client_ip):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded. Maximum {settings.rate_limit_requests} requests per {settings.rate_limit_window_seconds} seconds."
                },
            )

        return await call_next(request)
