"""
Unit tests for client.stt.recorder module (audio recording)
"""

from unittest.mock import MagicMock, patch

import numpy as np


class TestAudioRecorder:
    """Tests for AudioRecorder - push-to-talk audio capture"""

    def test_recorder_initializes_not_recording(self) -> None:
        """Recorder should not be recording on init"""
        from client.stt.recorder import AudioRecorder

        recorder = AudioRecorder(sample_rate=16000, channels=1)
        assert recorder.is_recording is False

    def test_recorder_stores_sample_rate(self) -> None:
        """Recorder should store the configured sample rate"""
        from client.stt.recorder import AudioRecorder

        recorder = AudioRecorder(sample_rate=44100, channels=1)
        assert recorder.sample_rate == 44100

    def test_recorder_stores_channels(self) -> None:
        """Recorder should store the configured channel count"""
        from client.stt.recorder import AudioRecorder

        recorder = AudioRecorder(sample_rate=16000, channels=2)
        assert recorder.channels == 2

    @patch("client.stt.recorder.SD_AVAILABLE", True)
    @patch("client.stt.recorder.sd")
    def test_start_recording_sets_is_recording_true(self, mock_sd: MagicMock) -> None:
        """start_recording should set is_recording to True"""
        from client.stt.recorder import AudioRecorder

        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.start_recording()
        assert recorder.is_recording is True

    @patch("client.stt.recorder.SD_AVAILABLE", True)
    @patch("client.stt.recorder.sd")
    def test_start_recording_opens_input_stream(self, mock_sd: MagicMock) -> None:
        """start_recording should create a sounddevice InputStream"""
        from client.stt.recorder import AudioRecorder

        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.start_recording()

        mock_sd.InputStream.assert_called_once()
        call_kwargs = mock_sd.InputStream.call_args[1]
        assert call_kwargs["samplerate"] == 16000
        assert call_kwargs["channels"] == 1
        mock_stream.start.assert_called_once()

    @patch("client.stt.recorder.SD_AVAILABLE", True)
    @patch("client.stt.recorder.sd")
    def test_stop_recording_returns_bytes_io_with_wav(self, mock_sd: MagicMock) -> None:
        """stop_recording should return BytesIO containing WAV data"""
        import io

        from client.stt.recorder import AudioRecorder

        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.start_recording()

        # Simulate audio data in the queue
        test_audio = np.zeros((1600, 1), dtype=np.int16)
        recorder._audio_queue.put(test_audio)

        result = recorder.stop_recording()

        assert isinstance(result, io.BytesIO)
        assert result.name == "recording.wav"
        assert result.tell() == 0  # Seek position at start
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        assert recorder.is_recording is False

    @patch("client.stt.recorder.SD_AVAILABLE", True)
    @patch("client.stt.recorder.sd")
    def test_stop_recording_without_audio_returns_none(self, mock_sd: MagicMock) -> None:
        """stop_recording with no captured audio should return None"""
        from client.stt.recorder import AudioRecorder

        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.start_recording()

        result = recorder.stop_recording()
        assert result is None

    def test_stop_recording_when_not_recording_returns_none(self) -> None:
        """stop_recording when not recording should return None"""
        from client.stt.recorder import AudioRecorder

        recorder = AudioRecorder(sample_rate=16000, channels=1)
        result = recorder.stop_recording()
        assert result is None
