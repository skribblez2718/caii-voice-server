"""
Shared test fixtures for caii-voice-server
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Set test environment before importing app modules
os.environ.setdefault("TTS_BASE_MODEL_PATH", "/mock/path/to/base/model")
os.environ.setdefault("TTS_VOICE_DESIGN_MODEL_PATH", "/mock/path/to/voice_design/model")
os.environ.setdefault("VOICES_DIRECTORY", str(Path(__file__).parent / "fixtures" / "voices"))


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for testing"""
    from app.config import Settings

    mock = MagicMock(spec=Settings)
    mock.host = "127.0.0.1"
    mock.port = 8001
    mock.voice_server_api_key = None
    mock.stt_model_name = "base"
    mock.stt_device = "cpu"
    mock.stt_compute_type = "float32"
    mock.stt_beam_size = 5
    mock.stt_best_of = 5
    mock.stt_vad_filter = True
    mock.voices_directory = Path(__file__).parent / "fixtures" / "voices"
    mock.tts_base_model_path = "/mock/path/to/base/model"
    mock.tts_voice_design_model_path = "/mock/path/to/voice_design/model"
    mock.rate_limit_requests = 10
    mock.rate_limit_window_seconds = 60
    mock.voices_json_path = mock.voices_directory / "voices.json"
    return mock


@pytest.fixture
def mock_tts_manager() -> MagicMock:
    """Create mock TTS manager for unit testing"""
    manager = MagicMock()
    manager.generate_speech = AsyncMock(return_value=b"RIFF" + b"\x00" * 40)  # Minimal WAV header
    manager.create_voice = AsyncMock(return_value=b"RIFF" + b"\x00" * 40)
    manager.transcribe_audio = AsyncMock(
        return_value={"text": "test transcription", "language": "en", "duration": 1.0}
    )
    manager.get_voice_prompt = MagicMock(return_value=[{"audio": b"test", "text": "test"}])
    manager.voice_config = MagicMock()
    manager.voice_config.default_voice = "da"
    manager.voice_config.voices = {"da": {"file": "da.wav", "description": "Default assistant"}}
    manager._initialized = True
    return manager


@pytest.fixture
def mock_base_model() -> MagicMock:
    """Create mock Qwen-TTS base model"""
    model = MagicMock()
    # create_voice_clone_prompt returns a List[VoiceClonePromptItem]
    # This is the key behavior we're testing - it returns a list, not a single item
    model.create_voice_clone_prompt = MagicMock(
        return_value=[{"audio_tokens": [1, 2, 3], "text": "Hello there!"}]
    )
    # generate_voice_clone expects voice_clone_prompt to be a list (not double-wrapped)
    model.generate_voice_clone = MagicMock(return_value=([b"\x00" * 1000], 24000))
    return model


def create_test_app(mock_tts_manager: MagicMock) -> FastAPI:
    """Create test app with mocked dependencies and no-op lifespan"""

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        # No-op lifespan for testing - models are mocked
        yield

    app = FastAPI(
        title="CAII Voice Server (Test)",
        description="Test instance",
        version="4.0.0",
        lifespan=test_lifespan,
    )

    # Import routes here to avoid circular imports
    from app.api.routes import router

    app.include_router(router)

    return app


@pytest.fixture
def test_client(mock_tts_manager: MagicMock) -> Generator[TestClient, None, None]:
    """Create test client with mocked TTS manager"""
    with patch("app.dependencies.tts_manager", mock_tts_manager):
        with patch("app.api.routes.tts.tts_manager", mock_tts_manager):
            app = create_test_app(mock_tts_manager)
            with TestClient(app) as client:
                yield client


@pytest.fixture
def voices_fixture_dir(tmp_path: Path) -> Path:
    """Create temporary voices directory with test fixtures"""
    voices_dir = tmp_path / "voices"
    voices_dir.mkdir()

    # Create minimal voices.json
    import json

    voices_json = {
        "default_voice": "da",
        "voices": {
            "da": {"file": "da.wav", "description": "Default assistant", "instruct": "friendly"},
            "analysis": {
                "file": "analysis.wav",
                "description": "Analysis agent",
                "instruct": "analytical",
            },
        },
    }
    (voices_dir / "voices.json").write_text(json.dumps(voices_json))

    return voices_dir
