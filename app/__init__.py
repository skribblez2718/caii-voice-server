"""
CAII Voice Server - Modular FastAPI application for TTS/STT
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.config import settings
from app.dependencies import tts_manager
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - handles startup and shutdown"""
    # Startup: Load models
    await tts_manager.startup()
    yield
    # Shutdown: Cleanup
    await tts_manager.shutdown()


def create_app() -> FastAPI:
    """Application factory"""
    app = FastAPI(
        title="CAII Voice Server",
        description="Modular TTS/STT server using Qwen-TTS and Faster-Whisper",
        version="4.0.0",
        lifespan=lifespan,
    )

    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)

    # Add auth middleware
    app.add_middleware(AuthMiddleware)

    # Include API routes
    app.include_router(router)

    return app


app = create_app()
