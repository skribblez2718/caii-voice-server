"""Route aggregation"""

from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.tts import router as tts_router
from app.api.routes.stt import router as stt_router
from app.api.routes.voice import router as voice_router

router = APIRouter()

# Include all route modules
router.include_router(health_router, tags=["Health"])
router.include_router(tts_router, prefix="/v1/audio", tags=["TTS"])
router.include_router(stt_router, prefix="/v1/audio", tags=["STT"])
router.include_router(voice_router, prefix="/v1", tags=["Voices"])
