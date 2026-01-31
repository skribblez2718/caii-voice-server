"""
Voice management routes
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.dependencies import tts_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateVoiceRequest(BaseModel):
    """Request to create a new voice"""

    agent_name: str = Field(
        ...,
        description="Name for the agent/voice (used as filename and identifier)",
    )
    instruct: str = Field(
        ...,
        description="Voice description for VoiceDesign model (e.g., 'Female, mid-thirties. Warm, smooth timbre...')",
    )


class VoiceInfo(BaseModel):
    """Voice information response"""

    name: str
    file: str
    description: str
    has_prompt: bool


@router.get("/voices")
async def list_voices():
    """List all available voices"""
    voices = []
    for name, info in tts_manager.voice_config.voices.items():
        voices.append(
            VoiceInfo(
                name=name,
                file=info["file"],
                description=info["description"],
                has_prompt=name in tts_manager.voice_prompts,
            )
        )

    return {
        "voices": [v.model_dump() for v in voices],
        "default_voice": tts_manager.voice_config.default_voice,
        "total": len(voices),
    }


@router.post("/voices")
async def create_voice(request: CreateVoiceRequest):
    """
    Create a new voice using VoiceDesign model

    The agent_name is used to:
    - Generate the intro text: "Hello there! I'm {Agent_name}, your AI assistant..."
    - Name the voice file: {agent_name}.wav
    - Create the voice configuration entry
    """
    # Validate agent name
    if not request.agent_name.isalnum() and "_" not in request.agent_name:
        raise HTTPException(
            status_code=400,
            detail="Agent name must be alphanumeric (underscores allowed)",
        )

    # Check if voice already exists
    if request.agent_name in tts_manager.voice_config.voices:
        raise HTTPException(
            status_code=409,
            detail=f"Voice for agent '{request.agent_name}' already exists. Delete it first to recreate.",
        )

    logger.info(f"Creating voice for agent '{request.agent_name}'")
    try:
        # Create the voice
        audio_bytes = await tts_manager.create_voice(
            agent_name=request.agent_name,
            instruct=request.instruct,
        )

        # Return the created audio
        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename={request.agent_name}.wav",
                "X-Agent-Voice": request.agent_name,
            },
        )

    except Exception as e:
        logger.error(f"Voice creation failed for agent '{request.agent_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Voice creation failed: {str(e)}")


@router.post("/voices/reload")
async def reload_voices():
    """Reload voice configuration and recompute voice prompts"""
    try:
        await tts_manager.reload_voice_prompts()
        return {
            "status": "success",
            "voices_loaded": len(tts_manager.voice_prompts),
            "message": "Voice configuration reloaded successfully",
        }
    except Exception as e:
        logger.error(f"Voice reload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reload voices: {str(e)}")
