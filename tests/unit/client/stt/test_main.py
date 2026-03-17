"""
Unit tests for client.stt.main module (PTT daemon entry point)
"""

from unittest.mock import MagicMock, patch


class TestPTTDaemon:
    """Tests for PTTDaemon - main push-to-talk orchestrator"""

    @patch("client.stt.main.PTTConfig")
    def test_daemon_initializes_with_config(self, mock_config_cls: MagicMock) -> None:
        """PTTDaemon should accept and store a PTTConfig"""
        from client.stt.main import PTTDaemon

        mock_config = MagicMock()
        mock_config.audio_sample_rate = 16000
        mock_config.audio_channels = 1
        mock_config.ptt_hotkey = "ctrl+alt+r"
        mock_config.server_url = "http://localhost:8001"
        mock_config.voice_server_api_key = "test-key"
        mock_config.injector_method = "auto"

        daemon = PTTDaemon(config=mock_config)
        assert daemon.config is mock_config

    @patch("client.stt.main.PTTConfig")
    def test_daemon_creates_recorder(self, mock_config_cls: MagicMock) -> None:
        """PTTDaemon should create an AudioRecorder with config settings"""
        from client.stt.main import PTTDaemon

        mock_config = MagicMock()
        mock_config.audio_sample_rate = 16000
        mock_config.audio_channels = 1
        mock_config.ptt_hotkey = "ctrl+alt+r"
        mock_config.server_url = "http://localhost:8001"
        mock_config.voice_server_api_key = "test-key"
        mock_config.injector_method = "auto"

        daemon = PTTDaemon(config=mock_config)
        assert daemon.recorder is not None

    @patch("client.stt.main.PTTConfig")
    def test_daemon_on_activate_starts_recording(self, mock_config_cls: MagicMock) -> None:
        """on_activate callback should start the recorder"""
        from client.stt.main import PTTDaemon

        mock_config = MagicMock()
        mock_config.audio_sample_rate = 16000
        mock_config.audio_channels = 1
        mock_config.ptt_hotkey = "ctrl+alt+r"
        mock_config.server_url = "http://localhost:8001"
        mock_config.voice_server_api_key = "test-key"
        mock_config.injector_method = "auto"

        daemon = PTTDaemon(config=mock_config)
        daemon.recorder = MagicMock()
        daemon.recorder.is_recording = False

        daemon.on_activate()
        daemon.recorder.start_recording.assert_called_once()

    @patch("client.stt.main.transcribe_audio", return_value="hello world")
    @patch("client.stt.main.inject_text")
    @patch("client.stt.main.PTTConfig")
    def test_daemon_on_deactivate_stops_and_transcribes(
        self,
        mock_config_cls: MagicMock,
        mock_inject: MagicMock,
        mock_transcribe: MagicMock,
    ) -> None:
        """on_deactivate should stop recording, transcribe, and inject text"""
        import io

        from client.stt.main import PTTDaemon

        mock_config = MagicMock()
        mock_config.audio_sample_rate = 16000
        mock_config.audio_channels = 1
        mock_config.ptt_hotkey = "ctrl+alt+r"
        mock_config.server_url = "http://localhost:8001"
        mock_config.voice_server_api_key = "test-key"
        mock_config.injector_method = "auto"

        daemon = PTTDaemon(config=mock_config)

        audio_buf = io.BytesIO(b"fake audio")
        audio_buf.name = "recording.wav"
        daemon.recorder = MagicMock()
        daemon.recorder.is_recording = True
        daemon.recorder.stop_recording.return_value = audio_buf

        daemon.on_deactivate()

        daemon.recorder.stop_recording.assert_called_once()
        mock_transcribe.assert_called_once_with(
            audio_data=audio_buf,
            server_url="http://localhost:8001",
            api_key="test-key",
        )
        mock_inject.assert_called_once_with("hello world", method="auto")

    @patch("client.stt.main.PTTConfig")
    def test_daemon_on_deactivate_no_audio_skips_transcribe(
        self, mock_config_cls: MagicMock
    ) -> None:
        """on_deactivate with no audio should skip transcription"""
        from client.stt.main import PTTDaemon

        mock_config = MagicMock()
        mock_config.audio_sample_rate = 16000
        mock_config.audio_channels = 1
        mock_config.ptt_hotkey = "ctrl+alt+r"
        mock_config.server_url = "http://localhost:8001"
        mock_config.voice_server_api_key = "test-key"
        mock_config.injector_method = "auto"

        daemon = PTTDaemon(config=mock_config)
        daemon.recorder = MagicMock()
        daemon.recorder.is_recording = True
        daemon.recorder.stop_recording.return_value = None

        # Should not raise
        daemon.on_deactivate()
