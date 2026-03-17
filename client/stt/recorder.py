"""
Audio recording module for push-to-talk STT client.

Uses sounddevice with a callback-based InputStream for non-blocking
audio capture. Records 16kHz mono int16 by default, outputs as
in-memory WAV via soundfile.
"""

import io
import logging
import queue
from typing import Optional

import numpy as np
import soundfile as sf

try:
    import sounddevice as sd

    SD_AVAILABLE = True
except (ImportError, OSError):
    sd = None  # type: ignore[assignment]
    SD_AVAILABLE = False

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Captures microphone audio for push-to-talk transcription.

    Args:
        sample_rate: Audio sample rate in Hz.
        channels: Number of audio channels (1 = mono).
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self._stream: Optional[sd.InputStream] = None
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        """Whether the recorder is currently capturing audio."""
        return self._is_recording

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """Sounddevice callback — stores audio chunks in the queue."""
        if status:
            logger.warning("Audio callback status: %s", status)
        self._audio_queue.put(indata.copy())

    def start_recording(self) -> None:
        """Begin capturing audio from the default input device."""
        if not SD_AVAILABLE:
            raise RuntimeError(
                "sounddevice is not available. Install PortAudio and sounddevice."
            )
        if self._is_recording:
            return

        # Clear any leftover audio from previous recordings
        while not self._audio_queue.empty():
            self._audio_queue.get_nowait()

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=self._audio_callback,
        )
        self._stream.start()
        self._is_recording = True
        logger.info("Recording started (rate=%d, channels=%d)", self.sample_rate, self.channels)

    def stop_recording(self) -> Optional[io.BytesIO]:
        """Stop capturing audio and return WAV data.

        Returns:
            BytesIO containing WAV data with .name='recording.wav',
            or None if no audio was captured or not recording.
        """
        if not self._is_recording:
            return None

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._is_recording = False

        # Collect all audio chunks
        chunks: list[np.ndarray] = []
        while not self._audio_queue.empty():
            chunks.append(self._audio_queue.get_nowait())

        if not chunks:
            logger.warning("Recording stopped but no audio was captured")
            return None

        audio_data = np.concatenate(chunks, axis=0)
        logger.info("Recording stopped: %d samples captured", len(audio_data))

        # Write to in-memory WAV buffer
        buf = io.BytesIO()
        sf.write(buf, audio_data, self.sample_rate, format="WAV", subtype="PCM_16")
        buf.seek(0)
        buf.name = "recording.wav"
        return buf
