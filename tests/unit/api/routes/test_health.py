"""
Unit tests for health endpoint
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for /health endpoint STT info"""

    def test_health_includes_stt_section(self) -> None:
        """Health response should include stt section with config info"""
        from fastapi import FastAPI

        from app.api.routes.health import router

        app = FastAPI()
        app.include_router(router)

        mock_manager = MagicMock()
        mock_manager.base_model = MagicMock()
        mock_manager.voice_design_model = MagicMock()
        mock_manager.stt_model = MagicMock()
        mock_manager.stt_load_seconds = 2.5
        mock_manager.voice_prompts = {"da": []}

        with patch("app.api.routes.health.tts_manager", mock_manager):
            with patch("app.api.routes.health.settings") as mock_settings:
                mock_settings.host = "127.0.0.1"
                mock_settings.port = 8001
                mock_settings.voice_server_api_key = None
                mock_settings.stt_model_name = "base"
                mock_settings.stt_device = "cuda"
                mock_settings.stt_compute_type = "float16"
                mock_settings.stt_beam_size = 5
                mock_settings.stt_best_of = 5
                mock_settings.stt_vad_filter = True

                client = TestClient(app)
                response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify stt section exists
        assert "stt" in data
        stt = data["stt"]

        # Verify all expected fields
        assert stt["model"] == "base"
        assert stt["device"] == "cuda"
        assert stt["compute_type"] == "float16"
        assert stt["beam_size"] == 5
        assert stt["best_of"] == 5
        assert stt["vad_filter"] is True
        assert stt["startup_load_seconds"] == 2.5

    def test_health_stt_section_reflects_settings(self) -> None:
        """Health stt section should reflect actual settings values"""
        from fastapi import FastAPI

        from app.api.routes.health import router

        app = FastAPI()
        app.include_router(router)

        mock_manager = MagicMock()
        mock_manager.base_model = MagicMock()
        mock_manager.voice_design_model = MagicMock()
        mock_manager.stt_model = MagicMock()
        mock_manager.stt_load_seconds = 5.0
        mock_manager.voice_prompts = {}

        with patch("app.api.routes.health.tts_manager", mock_manager):
            with patch("app.api.routes.health.settings") as mock_settings:
                mock_settings.host = "0.0.0.0"
                mock_settings.port = 8765
                mock_settings.voice_server_api_key = "secret"
                mock_settings.stt_model_name = "large-v3"
                mock_settings.stt_device = "cpu"
                mock_settings.stt_compute_type = "int8"
                mock_settings.stt_beam_size = 10
                mock_settings.stt_best_of = 3
                mock_settings.stt_vad_filter = False

                client = TestClient(app)
                response = client.get("/health")

        data = response.json()
        stt = data["stt"]

        assert stt["model"] == "large-v3"
        assert stt["device"] == "cpu"
        assert stt["compute_type"] == "int8"
        assert stt["beam_size"] == 10
        assert stt["best_of"] == 3
        assert stt["vad_filter"] is False
        assert stt["startup_load_seconds"] == 5.0
