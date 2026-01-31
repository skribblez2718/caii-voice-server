"""
API Key Authentication Middleware
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

# Paths that don't require authentication
EXEMPT_PATHS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for API key validation"""

    async def dispatch(self, request: Request, call_next):
        # Skip auth if no API key is configured
        if not settings.voice_server_api_key:
            return await call_next(request)

        # Skip auth for exempt paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Check for API key in headers
        api_key = None

        # Check X-API-Key header
        if "x-api-key" in request.headers:
            api_key = request.headers["x-api-key"]

        # Check Authorization header (Bearer token)
        elif "authorization" in request.headers:
            auth_header = request.headers["authorization"]
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]  # Remove "Bearer " prefix

        # Validate API key
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing API key. Use X-API-Key header or Bearer token."},
            )

        if api_key != settings.voice_server_api_key:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key"},
            )

        return await call_next(request)
