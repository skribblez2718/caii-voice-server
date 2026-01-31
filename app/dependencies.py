"""
Dependencies module - Model loading and voice prompt management
"""

import io
import logging
from typing import Optional

import numpy as np
import soundfile as sf
import torch

from app.config import settings, VoiceConfig

logger = logging.getLogger(__name__)


class TTSManager:
    """Manages TTS models and voice prompts"""

    def __init__(self):
        self.base_model = None  # For voice cloning
        self.voice_design_model = None  # For voice creation
        self.stt_model = None  # For speech-to-text
        self.voice_prompts: dict = {}  # Cached voice prompts
        self.voice_config = VoiceConfig(settings)
        self._initialized = False

    async def startup(self) -> None:
        """Load models and pre-compute voice prompts at startup"""
        if self._initialized:
            return

        logger.info("Loading TTS Base model for voice cloning...")
        await self._load_base_model()

        logger.info("Loading TTS VoiceDesign model for voice creation...")
        await self._load_voice_design_model()

        logger.info("Loading STT model (faster-whisper)...")
        await self._load_stt_model()

        logger.info("Pre-computing voice prompts for all agents...")
        await self._precompute_voice_prompts()

        self._initialized = True
        logger.info("All models loaded and voice prompts cached")

    async def shutdown(self) -> None:
        """Cleanup resources"""
        self.base_model = None
        self.voice_design_model = None
        self.stt_model = None
        self.voice_prompts.clear()
        self._initialized = False
        logger.info("TTS Manager shutdown complete")

    async def _load_base_model(self) -> None:
        """Load Qwen-TTS Base model for voice cloning"""
        try:
            from qwen_tts import Qwen3TTSModel

            self.base_model = Qwen3TTSModel.from_pretrained(
                settings.tts_base_model_path,
                local_files_only=True,
                device_map="cuda:0",
                dtype=torch.bfloat16,
            )
            logger.info(f"Base model loaded from {settings.tts_base_model_path}")
        except Exception as e:
            logger.error(f"Failed to load Base model: {e}")
            raise

    async def _load_voice_design_model(self) -> None:
        """Load Qwen-TTS VoiceDesign model for voice creation"""
        try:
            from qwen_tts import Qwen3TTSModel

            self.voice_design_model = Qwen3TTSModel.from_pretrained(
                settings.tts_voice_design_model_path,
                local_files_only=True,
                device_map="cuda:0",
                dtype=torch.bfloat16,
            )
            logger.info(
                f"VoiceDesign model loaded from {settings.tts_voice_design_model_path}"
            )
        except Exception as e:
            logger.error(f"Failed to load VoiceDesign model: {e}")
            raise

    async def _load_stt_model(self) -> None:
        """Load faster-whisper STT model"""
        try:
            from faster_whisper import WhisperModel

            self.stt_model = WhisperModel(
                settings.stt_model_name,
                device=settings.stt_device,
                compute_type=settings.stt_compute_type,
            )
            logger.info(
                f"STT model '{settings.stt_model_name}' loaded on {settings.stt_device}"
            )
        except Exception as e:
            logger.error(f"Failed to load STT model: {e}")
            raise

    async def _precompute_voice_prompts(self) -> None:
        """Pre-compute voice prompts for all configured agents"""
        for agent_name, voice_info in self.voice_config.voices.items():
            voice_file = settings.voices_directory / voice_info["file"]
            if voice_file.exists():
                ref_text = self.voice_config.get_ref_text(agent_name)
                try:
                    prompt = self.base_model.create_voice_clone_prompt(
                        ref_audio=str(voice_file),
                        ref_text=ref_text,
                    )
                    self.voice_prompts[agent_name] = prompt
                    logger.info(f"Voice prompt cached for agent: {agent_name}")
                except Exception as e:
                    logger.error(f"Failed to create voice prompt for {agent_name}: {e}")
            else:
                logger.warning(f"Voice file not found for {agent_name}: {voice_file}")

    def get_voice_prompt(self, agent_name: str) -> Optional[list]:
        """Get cached voice prompt for an agent"""
        return self.voice_prompts.get(agent_name)

    async def reload_voice_prompts(self) -> None:
        """Reload voice configuration and recompute prompts"""
        self.voice_config.load()
        self.voice_prompts.clear()
        await self._precompute_voice_prompts()

    async def generate_speech(self, text: str, agent_name: str) -> bytes:
        """Generate speech using voice cloning"""
        voice_prompt = self.get_voice_prompt(agent_name)

        if voice_prompt is None:
            # Fall back to default voice
            default_agent = self.voice_config.default_voice
            voice_prompt = self.get_voice_prompt(default_agent)
            if voice_prompt is None:
                raise ValueError(f"No voice prompt available for {agent_name} or default")
            logger.warning(f"Using default voice '{default_agent}' for agent '{agent_name}'")

        # Check model is loaded
        if self.base_model is None:
            raise RuntimeError("TTS base model not loaded")

        # Generate speech with logging
        logger.info(f"Generating speech: agent='{agent_name}', text_length={len(text)}")
        try:
            wavs, sr = self.base_model.generate_voice_clone(
                text=text,
                language="English",
                voice_clone_prompt=[voice_prompt],
            )
        except Exception as e:
            logger.error(f"Model generation failed: {e}", exc_info=True)
            raise

        # Convert to WAV bytes
        try:
            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, wavs[0], sr, format="WAV")
            audio_bytes = audio_buffer.getvalue()
            logger.debug(f"Generated {len(audio_bytes)} bytes of audio")
            return audio_bytes
        except Exception as e:
            logger.error(f"WAV encoding failed: {e}", exc_info=True)
            raise

    async def create_voice(self, agent_name: str, instruct: str) -> bytes:
        """Create a new voice using VoiceDesign model"""
        logger.info(f"Creating voice: agent='{agent_name}'")

        if self.voice_design_model is None:
            raise RuntimeError("VoiceDesign model not loaded")

        # Generate standard intro text
        text = self.voice_config.get_ref_text(agent_name)

        # Generate voice
        try:
            wavs, sr = self.voice_design_model.generate_voice_design(
                text=text,
                language="English",
                instruct=instruct,
            )
        except Exception as e:
            logger.error(f"Voice design generation failed: {e}", exc_info=True)
            raise

        # Save to file
        voice_file = f"{agent_name}.wav"
        voice_path = settings.voices_directory / voice_file
        try:
            sf.write(str(voice_path), wavs[0], sr)
        except Exception as e:
            logger.error(f"Failed to save voice file '{voice_path}': {e}", exc_info=True)
            raise

        # Add to configuration
        self.voice_config.add_voice(
            agent_name=agent_name,
            file=voice_file,
            description=instruct[:100],  # Truncate for description
            instruct=instruct,
        )

        # Create and cache voice prompt for new voice
        try:
            ref_text = self.voice_config.get_ref_text(agent_name)
            prompt = self.base_model.create_voice_clone_prompt(
                ref_audio=str(voice_path),
                ref_text=ref_text,
            )
            self.voice_prompts[agent_name] = prompt
        except Exception as e:
            logger.error(f"Failed to create voice prompt for '{agent_name}': {e}", exc_info=True)
            raise

        logger.info(f"Created new voice for agent: {agent_name}")

        # Return audio bytes
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, wavs[0], sr, format="WAV")
        return audio_buffer.getvalue()

    async def transcribe_audio(
        self, audio_bytes: bytes, language: Optional[str] = None
    ) -> dict:
        """Transcribe audio using faster-whisper"""
        logger.info(f"Transcribing audio: size={len(audio_bytes)} bytes, language={language}")

        if self.stt_model is None:
            raise RuntimeError("STT model not loaded")

        from pydub import AudioSegment

        # Load audio from bytes
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        except Exception as e:
            logger.error(f"Failed to load audio file: {e}", exc_info=True)
            raise

        # Convert to 16kHz mono
        audio = audio.set_frame_rate(16000).set_channels(1)

        # Convert to numpy array
        audio_array = (
            np.frombuffer(audio.raw_data, np.int16).flatten().astype(np.float32)
            / 32768.0
        )

        # Transcribe
        try:
            segments, info = self.stt_model.transcribe(
                audio_array,
                language=language or "en",
            )
        except Exception as e:
            logger.error(f"STT transcription failed: {e}", exc_info=True)
            raise

        # Combine segments
        full_text = " ".join(seg.text.strip() for seg in segments)

        logger.debug(f"Transcription complete: {len(full_text)} chars, language={info.language}")
        return {
            "text": full_text,
            "language": info.language,
            "duration": info.duration,
        }


# Global TTS manager instance
tts_manager = TTSManager()
