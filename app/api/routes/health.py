"""
Health check routes
"""

import time

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
        "stt": {
            "model": settings.stt_model_name,
            "device": settings.stt_device,
            "compute_type": settings.stt_compute_type,
            "beam_size": settings.stt_beam_size,
            "best_of": settings.stt_best_of,
            "vad_filter": settings.stt_vad_filter,
            "startup_load_seconds": tts_manager.stt_load_seconds,
        },
        "voices_loaded": len(tts_manager.voice_prompts),
        "auth_enabled": settings.voice_server_api_key is not None,
        "model_offload": {
            "enabled": settings.model_offload_enabled,
            "location": tts_manager._model_location,
            "idle_timeout_seconds": settings.model_idle_timeout_seconds,
            "seconds_since_last_request": (
                time.time() - tts_manager._last_tts_request_time
                if tts_manager._last_tts_request_time > 0 else 0
            ),
        },
    }
