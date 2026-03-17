"""
Unit tests for client.stt.transcriber module (voice server API client)
"""

import io
import json
from unittest.mock import MagicMock, patch


class TestTranscribeAudio:
    """Tests for transcribe_audio - send audio to voice server"""

    @patch("client.stt.transcriber.urllib.request.urlopen")
    def test_transcribe_returns_text(self, mock_urlopen: MagicMock) -> None:
        """transcribe_audio should return the transcribed text"""
        from client.stt.transcriber import transcribe_audio

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"text": "hello world"}).encode()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        audio_buf = io.BytesIO(b"fake wav data")
        audio_buf.name = "recording.wav"

        result = transcribe_audio(
            audio_data=audio_buf,
            server_url="http://localhost:8001",
            api_key="test-key",
        )

        assert result == "hello world"

    @patch("client.stt.transcriber.urllib.request.urlopen")
    def test_transcribe_sends_to_correct_endpoint(self, mock_urlopen: MagicMock) -> None:
        """transcribe_audio should POST to /v1/audio/transcriptions"""
        from client.stt.transcriber import transcribe_audio

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"text": "test"}).encode()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        audio_buf = io.BytesIO(b"fake wav data")
        audio_buf.name = "recording.wav"

        transcribe_audio(
            audio_data=audio_buf,
            server_url="http://localhost:8001",
            api_key="test-key",
        )

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.full_url == "http://localhost:8001/v1/audio/transcriptions"

    @patch("client.stt.transcriber.urllib.request.urlopen")
    def test_transcribe_sends_auth_header(self, mock_urlopen: MagicMock) -> None:
        """transcribe_audio should include Authorization Bearer header"""
        from client.stt.transcriber import transcribe_audio

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"text": "test"}).encode()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        audio_buf = io.BytesIO(b"fake wav data")
        audio_buf.name = "recording.wav"

        transcribe_audio(
            audio_data=audio_buf,
            server_url="http://localhost:8001",
            api_key="my-secret-key",
        )

        request = mock_urlopen.call_args[0][0]
        assert request.get_header("Authorization") == "Bearer my-secret-key"

    @patch("client.stt.transcriber.urllib.request.urlopen")
    def test_transcribe_sends_multipart_form_data(self, mock_urlopen: MagicMock) -> None:
        """transcribe_audio should send multipart/form-data with file and model fields"""
        from client.stt.transcriber import transcribe_audio

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"text": "test"}).encode()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        audio_buf = io.BytesIO(b"fake wav data")
        audio_buf.name = "recording.wav"

        transcribe_audio(
            audio_data=audio_buf,
            server_url="http://localhost:8001",
            api_key="test-key",
        )

        request = mock_urlopen.call_args[0][0]
        content_type = request.get_header("Content-type")
        assert "multipart/form-data" in content_type
        body = request.data
        assert b"recording.wav" in body
        assert b"whisper-1" in body

    @patch("client.stt.transcriber.urllib.request.urlopen")
    def test_transcribe_handles_text_response_format(self, mock_urlopen: MagicMock) -> None:
        """transcribe_audio with response_format='text' returns plain text"""
        from client.stt.transcriber import transcribe_audio

        mock_response = MagicMock()
        mock_response.read.return_value = b"hello plain text"
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        audio_buf = io.BytesIO(b"fake wav data")
        audio_buf.name = "recording.wav"

        result = transcribe_audio(
            audio_data=audio_buf,
            server_url="http://localhost:8001",
            api_key="test-key",
            response_format="text",
        )

        assert result == "hello plain text"
