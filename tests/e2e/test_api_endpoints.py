"""
End-to-end tests for API endpoints
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestTTSEndpoint:
    """Tests for /v1/audio/speech endpoint"""

    def test_tts_endpoint_returns_audio(
        self, test_client: TestClient, mock_tts_manager: MagicMock
    ) -> None:
        """TTS endpoint should return WAV audio"""
        response = test_client.post(
            "/v1/audio/speech",
            json={"input": "Hello world", "voice": "alloy"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert "X-Agent-Voice" in response.headers

    def test_tts_endpoint_uses_agent_parameter(
        self, test_client: TestClient, mock_tts_manager: MagicMock
    ) -> None:
        """TTS endpoint should use agent parameter for voice selection"""
        response = test_client.post(
            "/v1/audio/speech",
            json={"input": "Hello world", "agent": "analysis"},
        )

        assert response.status_code == 200
        # Verify the correct agent was used
        mock_tts_manager.generate_speech.assert_called_once()
        call_kwargs = mock_tts_manager.generate_speech.call_args.kwargs
        assert call_kwargs["agent_name"] == "analysis"

    def test_tts_endpoint_validates_empty_input(
        self, test_client: TestClient, mock_tts_manager: MagicMock
    ) -> None:
        """TTS endpoint should reject empty input"""
        response = test_client.post(
            "/v1/audio/speech",
            json={"input": "   "},  # Whitespace only
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_tts_endpoint_validates_input_length(
        self, test_client: TestClient, mock_tts_manager: MagicMock
    ) -> None:
        """TTS endpoint should reject input exceeding 4096 characters"""
        response = test_client.post(
            "/v1/audio/speech",
            json={"input": "x" * 5000},
        )

        assert response.status_code == 400
        assert "4096" in response.json()["detail"]

    def test_tts_endpoint_uses_default_voice(
        self, test_client: TestClient, mock_tts_manager: MagicMock
    ) -> None:
        """TTS endpoint should use default voice when agent not specified"""
        response = test_client.post(
            "/v1/audio/speech",
            json={"input": "Hello world"},
        )

        assert response.status_code == 200
        mock_tts_manager.generate_speech.assert_called_once()
        call_kwargs = mock_tts_manager.generate_speech.call_args.kwargs
        assert call_kwargs["agent_name"] == "da"  # Default voice


class TestHealthEndpoint:
    """Tests for health check endpoints"""

    def test_health_endpoint_returns_ok(
        self, test_client: TestClient, mock_tts_manager: MagicMock
    ) -> None:
        """Health endpoint should return healthy status"""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
