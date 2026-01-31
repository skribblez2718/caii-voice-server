"""
CAII Voice Server - Entry Point

Modular FastAPI application for TTS/STT using:
- Qwen-TTS for voice cloning and voice creation
- Faster-Whisper for speech-to-text
"""

import logging

import uvicorn

from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        access_log=True,
    )
