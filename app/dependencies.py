"""
Dependencies module - Model loading and voice prompt management
"""

import asyncio
import io
import logging
import time
from typing import Optional

import numpy as np
import soundfile as sf
import torch

from app.config import VoiceConfig, settings

logger = logging.getLogger(__name__)


class TTSManager:
    """Manages TTS models and voice prompts"""

    def __init__(self):
        self.base_model = None  # For voice cloning
        self.voice_design_model = None  # For voice creation
        self.stt_model = None  # For speech-to-text
        self.stt_load_seconds: float = 0.0  # STT model load time
        self.voice_prompts: dict = {}  # Cached voice prompts
        self.voice_config = VoiceConfig(settings)
        self._initialized = False

        # Offload state tracking
        self._last_tts_request_time: float = 0.0
        self._model_location: str = "unloaded"  # "cuda", "cpu", "unloaded"
        self._offload_lock: asyncio.Lock = asyncio.Lock()
        self._offload_task: Optional[asyncio.Task] = None
        self._shutdown_event: asyncio.Event = asyncio.Event()

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

        self._model_location = "cuda"
        self._last_tts_request_time = time.time()
        if settings.model_offload_enabled:
            self._offload_task = asyncio.create_task(self._offload_monitor_loop())

        self._initialized = True
        logger.info("All models loaded and voice prompts cached")

    async def shutdown(self) -> None:
        """Cleanup resources"""
        if self._offload_task:
            self._shutdown_event.set()
            try:
                await asyncio.wait_for(self._offload_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._offload_task.cancel()

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
            logger.info(f"VoiceDesign model loaded from {settings.tts_voice_design_model_path}")
        except Exception as e:
            logger.error(f"Failed to load VoiceDesign model: {e}")
            raise

    async def _load_stt_model(self) -> None:
        """Load faster-whisper STT model"""
        try:
            from faster_whisper import WhisperModel

            start_time = time.time()
            self.stt_model = WhisperModel(
                settings.stt_model_name,
                device=settings.stt_device,
                compute_type=settings.stt_compute_type,
            )
            self.stt_load_seconds = time.time() - start_time
            logger.info(
                f"STT model '{settings.stt_model_name}' loaded on {settings.stt_device} "
                f"in {self.stt_load_seconds:.2f}s"
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

    async def _offload_to_cpu(self) -> None:
        """Move TTS models to CPU and free GPU memory"""
        async with self._offload_lock:
            if self._model_location != "cuda":
                return

            logger.info("Offloading TTS models to CPU...")
            if self.base_model is not None:
                self.base_model = self.base_model.cpu()
            if self.voice_design_model is not None:
                self.voice_design_model = self.voice_design_model.cpu()

            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            self._model_location = "cpu"
            logger.info("Models offloaded to CPU, GPU memory freed")

    async def _ensure_models_on_gpu(self) -> None:
        """Ensure TTS models are on GPU (reload if needed)"""
        async with self._offload_lock:
            if self._model_location == "cuda":
                return

            logger.info(f"Loading TTS models to GPU (from {self._model_location})...")
            start = time.time()

            if self._model_location == "cpu":
                if self.base_model is not None:
                    self.base_model = self.base_model.cuda()
                if self.voice_design_model is not None:
                    self.voice_design_model = self.voice_design_model.cuda()
            else:  # unloaded
                await self._load_base_model()
                await self._load_voice_design_model()
                await self._precompute_voice_prompts()

            self._model_location = "cuda"
            logger.info(f"Models loaded to GPU in {time.time() - start:.2f}s")

    async def _offload_monitor_loop(self) -> None:
        """Background task checking idle time"""
        logger.info("Model offload monitor started")
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=settings.model_offload_check_interval_seconds
                )
                break
            except asyncio.TimeoutError:
                pass

            if not settings.model_offload_enabled or self._last_tts_request_time == 0:
                continue

            idle = time.time() - self._last_tts_request_time
            if idle >= settings.model_idle_timeout_seconds:
                try:
                    await self._offload_to_cpu()
                except Exception as e:
                    logger.error(f"Offload failed: {e}")
        logger.info("Model offload monitor stopped")

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
        await self._ensure_models_on_gpu()
        self._last_tts_request_time = time.time()

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
            # voice_prompt is already a List[VoiceClonePromptItem] from create_voice_clone_prompt()
            # Do NOT wrap it in another list - that causes double-wrapping bug
            wavs, sr = self.base_model.generate_voice_clone(
                text=text,
                language="English",
                voice_clone_prompt=voice_prompt,
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
        await self._ensure_models_on_gpu()
        self._last_tts_request_time = time.time()

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

    async def transcribe_audio(self, audio_bytes: bytes, language: Optional[str] = None) -> dict:
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
        audio_array = np.frombuffer(audio.raw_data, np.int16).flatten().astype(np.float32) / 32768.0

        # Transcribe with configured options
        try:
            segments, info = self.stt_model.transcribe(
                audio_array,
                beam_size=settings.stt_beam_size,
                best_of=settings.stt_best_of,
                vad_filter=settings.stt_vad_filter,
                language=language,  # Auto-detect if None
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
