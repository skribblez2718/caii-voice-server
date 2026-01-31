"""
Health check routes
"""

from fastapi import APIRouter

from app.config import settings
from app.dependencies import tts_manager

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint - server info"""
    return {
        "name": "CAII Voice Server",
        "description": "Modular TTS/STT server using Qwen-TTS and Faster-Whisper",
        "version": "4.0.0",
        "endpoints": {
            "tts": "/v1/audio/speech",
            "stt": "/v1/audio/transcriptions",
            "voices": "/v1/voices",
            "health": "/health",
        },
    }


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "host": settings.host,
        "port": settings.port,
        "models": {
            "tts_base": tts_manager.base_model is not None,
            "tts_voice_design": tts_manager.voice_design_model is not None,
            "stt": tts_manager.stt_model is not None,
        },
        "voices_loaded": len(tts_manager.voice_prompts),
        "auth_enabled": settings.voice_server_api_key is not None,
    }
