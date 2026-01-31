"""
Unit tests for app.config module
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

from app.config import VoiceConfig


class TestSettingsSTTConfig:
    """Tests for STT configuration settings"""

    def test_stt_beam_size_has_default(self) -> None:
        """stt_beam_size should default to 5"""
        from app.config import Settings

        settings = Settings(
            tts_base_model_path="/mock/path",
            tts_voice_design_model_path="/mock/path",
        )
        assert settings.stt_beam_size == 5

    def test_stt_best_of_has_default(self) -> None:
        """stt_best_of should default to 5"""
        from app.config import Settings

        settings = Settings(
            tts_base_model_path="/mock/path",
            tts_voice_design_model_path="/mock/path",
        )
        assert settings.stt_best_of == 5

    def test_stt_vad_filter_has_default(self) -> None:
        """stt_vad_filter should default to True"""
        from app.config import Settings

        settings = Settings(
            tts_base_model_path="/mock/path",
            tts_voice_design_model_path="/mock/path",
        )
        assert settings.stt_vad_filter is True

    def test_stt_beam_size_from_env(self, monkeypatch) -> None:
        """stt_beam_size should be overridable via env var"""
        monkeypatch.setenv("STT_BEAM_SIZE", "10")
        from importlib import reload

        import app.config as config_module

        reload(config_module)
        settings = config_module.Settings(
            tts_base_model_path="/mock/path",
            tts_voice_design_model_path="/mock/path",
        )
        assert settings.stt_beam_size == 10

    def test_stt_best_of_from_env(self, monkeypatch) -> None:
        """stt_best_of should be overridable via env var"""
        monkeypatch.setenv("STT_BEST_OF", "3")
        from importlib import reload

        import app.config as config_module

        reload(config_module)
        settings = config_module.Settings(
            tts_base_model_path="/mock/path",
            tts_voice_design_model_path="/mock/path",
        )
        assert settings.stt_best_of == 3

    def test_stt_vad_filter_from_env(self, monkeypatch) -> None:
        """stt_vad_filter should be overridable via env var"""
        monkeypatch.setenv("STT_VAD_FILTER", "false")
        from importlib import reload

        import app.config as config_module

        reload(config_module)
        settings = config_module.Settings(
            tts_base_model_path="/mock/path",
            tts_voice_design_model_path="/mock/path",
        )
        assert settings.stt_vad_filter is False


class TestVoiceConfig:
    """Tests for VoiceConfig class"""

    def test_load_creates_default_config_when_file_missing(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """VoiceConfig should create default config when voices.json doesn't exist"""
        mock_settings.voices_directory = tmp_path
        mock_settings.voices_json_path = tmp_path / "voices.json"

        config = VoiceConfig(mock_settings)

        assert config.default_voice == "da"
        assert config.voices == {}

    def test_load_reads_existing_config(self, mock_settings: MagicMock, tmp_path: Path) -> None:
        """VoiceConfig should load existing voices.json"""
        mock_settings.voices_directory = tmp_path
        mock_settings.voices_json_path = tmp_path / "voices.json"

        # Create test config
        test_config = {
            "default_voice": "analysis",
            "voices": {"analysis": {"file": "analysis.wav", "description": "Test"}},
        }
        (tmp_path / "voices.json").write_text(json.dumps(test_config))

        config = VoiceConfig(mock_settings)

        assert config.default_voice == "analysis"
        assert "analysis" in config.voices

    def test_get_voice_returns_voice_config(self, mock_settings: MagicMock, tmp_path: Path) -> None:
        """get_voice should return voice configuration for existing agent"""
        mock_settings.voices_directory = tmp_path
        mock_settings.voices_json_path = tmp_path / "voices.json"

        test_config = {
            "default_voice": "da",
            "voices": {"da": {"file": "da.wav", "description": "Default assistant"}},
        }
        (tmp_path / "voices.json").write_text(json.dumps(test_config))

        config = VoiceConfig(mock_settings)
        voice = config.get_voice("da")

        assert voice is not None
        assert voice["file"] == "da.wav"

    def test_get_voice_returns_none_for_unknown_agent(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """get_voice should return None for non-existent agent"""
        mock_settings.voices_directory = tmp_path
        mock_settings.voices_json_path = tmp_path / "voices.json"

        config = VoiceConfig(mock_settings)

        assert config.get_voice("nonexistent") is None

    def test_get_ref_text_generates_expected_format(
        self, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """get_ref_text should generate properly formatted reference text"""
        mock_settings.voices_directory = tmp_path
        mock_settings.voices_json_path = tmp_path / "voices.json"

        config = VoiceConfig(mock_settings)
        ref_text = config.get_ref_text("analysis")

        assert "Analysis" in ref_text  # Capitalized
        assert "AI assistant" in ref_text

    def test_add_voice_saves_to_json(self, mock_settings: MagicMock, tmp_path: Path) -> None:
        """add_voice should persist new voice to voices.json"""
        mock_settings.voices_directory = tmp_path
        mock_settings.voices_json_path = tmp_path / "voices.json"

        config = VoiceConfig(mock_settings)
        config.add_voice(
            agent_name="newagent",
            file="newagent.wav",
            description="New agent voice",
            instruct="be helpful",
        )

        # Reload and verify
        config.load()
        voice = config.get_voice("newagent")
        assert voice is not None
        assert voice["file"] == "newagent.wav"
        assert voice["description"] == "New agent voice"
