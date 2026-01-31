"""
Text-to-Speech routes (OpenAI-compatible)
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.dependencies import tts_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class TTSRequest(BaseModel):
    """OpenAI-compatible TTS request with agent extension"""

    model: str = Field(
        default="tts-1",
        description="Model name (tts-1, tts-1-hd) - ignored, uses Qwen-TTS",
    )
    input: str = Field(..., description="Text to synthesize (max 4096 chars)")
    voice: str = Field(
        default="alloy",
        description="Voice name (OpenAI compatibility) - use 'agent' parameter instead",
    )
    response_format: Optional[str] = Field(
        default="wav",
        description="Response format (wav recommended for local TTS)",
    )
    speed: Optional[float] = Field(
        default=1.0,
        description="Speed (0.25 to 4.0) - not currently supported",
    )
    agent: Optional[str] = Field(
        default=None,
        description="Agent name for voice selection (da, analysis, clarification, etc.)",
    )


@router.post("/speech")
async def text_to_speech(request: TTSRequest):
    """
    OpenAI-compatible Text-to-Speech endpoint

    Uses Qwen-TTS for voice cloning. The 'agent' parameter selects which
    agent voice to use. If not specified, uses the default voice.
    """
    # Validate input length
    if len(request.input) > 4096:
        raise HTTPException(
            status_code=400, detail="Input text exceeds 4096 character limit"
        )

    if not request.input.strip():
        raise HTTPException(status_code=400, detail="Input text is empty")

    # Determine agent voice to use
    agent_name = request.agent or tts_manager.voice_config.default_voice

    try:
        # Generate speech
        audio_bytes = await tts_manager.generate_speech(
            text=request.input,
            agent_name=agent_name,
        )

        # Return audio stream
        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=speech.wav",
                "X-Agent-Voice": agent_name,
            },
        )

    except ValueError as e:
        logger.warning(f"TTS validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TTS generation failed for agent '{agent_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Speech generation failed: {str(e)}")
