"""
Speech-to-Text routes (OpenAI-compatible)
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.dependencies import tts_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/transcriptions")
async def speech_to_text(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    model: str = Form(
        default="whisper-1",
        description="Model name (whisper-1) - ignored, uses faster-whisper",
    ),
    language: Optional[str] = Form(
        default=None,
        description="Language code (e.g., 'en', 'es')",
    ),
    prompt: Optional[str] = Form(
        default=None,
        description="Optional prompt for context - not currently supported",
    ),
    response_format: str = Form(
        default="json",
        description="Response format (json, text, verbose_json)",
    ),
    temperature: Optional[float] = Form(
        default=None,
        description="Temperature (0.0 to 1.0) - not currently supported",
    ),
):
    """
    OpenAI-compatible Speech-to-Text endpoint

    Uses faster-whisper for local transcription.
    """
    try:
        # Read audio content
        audio_bytes = await file.read()
        logger.info(f"STT request: file={file.filename}, size={len(audio_bytes)} bytes, language={language}")

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Transcribe
        result = await tts_manager.transcribe_audio(
            audio_bytes=audio_bytes,
            language=language,
        )

        # Handle response formats
        if response_format == "text":
            return PlainTextResponse(content=result["text"])

        elif response_format == "verbose_json":
            return {
                "task": "transcribe",
                "language": result["language"],
                "duration": result["duration"],
                "text": result["text"],
                "segments": [
                    {
                        "id": 0,
                        "seek": 0,
                        "start": 0.0,
                        "end": result["duration"],
                        "text": result["text"],
                        "tokens": [],
                        "temperature": temperature or 0.0,
                        "avg_logprob": 0.0,
                        "compression_ratio": 1.0,
                        "no_speech_prob": 0.0,
                    }
                ],
            }

        else:  # json (default)
            return {"text": result["text"]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed for file '{file.filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
