"""
Configuration module using pydantic-settings
"""

import json
from pathlib import Path
from typing import Optional
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server settings
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8001, description="Server port")

    # API key authentication
    voice_server_api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication. If not set, auth is disabled.",
    )

    stt_model_name: str = Field(
        default="base",
        description="Faster-whisper model name (tiny, base, small, medium, large)",
    )
    stt_device: str = Field(
        default="cuda",
        description="Device for STT model (cuda, cpu)",
    )
    stt_compute_type: str = Field(
        default="float16",
        description="Compute type for STT model",
    )

    # Voice settings
    # Default uses working directory (service sets WorkingDirectory=/home/caii-voice-server)
    voices_directory: Path = Field(
        default=Path("voices"),
        description="Directory containing voice files (voices.json and *.wav)",
    )

    # Model paths - REQUIRED, must be set in .env
    tts_base_model_path: str = Field(
        description="Path to Qwen-TTS Base model for voice cloning",
    )
    tts_voice_design_model_path: str = Field(
        description="Path to Qwen-TTS VoiceDesign model for voice creation",
    )

    # Rate limiting
    rate_limit_requests: int = Field(
        default=10,
        description="Maximum requests per rate limit window",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        description="Rate limit window in seconds",
    )

    @property
    def voices_json_path(self) -> Path:
        return self.voices_directory / "voices.json"


class VoiceConfig:
    """Voice configuration manager"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._config: dict = {}
        self.load()

    def load(self) -> None:
        """Load voice configuration from JSON file"""
        if self.settings.voices_json_path.exists():
            with open(self.settings.voices_json_path, "r") as f:
                self._config = json.load(f)
        else:
            self._config = {"voices": {}, "default_voice": "da"}

    def save(self) -> None:
        """Save voice configuration to JSON file"""
        with open(self.settings.voices_json_path, "w") as f:
            json.dump(self._config, f, indent=2)

    @property
    def voices(self) -> dict:
        """Get all voice configurations"""
        return self._config.get("voices", {})

    @property
    def default_voice(self) -> str:
        """Get default voice name"""
        return self._config.get("default_voice", "da")

    def get_voice(self, agent_name: str) -> Optional[dict]:
        """Get voice configuration for an agent"""
        return self.voices.get(agent_name)

    def get_voice_file_path(self, agent_name: str) -> Optional[Path]:
        """Get full path to voice file for an agent"""
        voice = self.get_voice(agent_name)
        if voice:
            return self.settings.voices_directory / voice["file"]
        return None

    def add_voice(
        self, agent_name: str, file: str, description: str, instruct: str
    ) -> None:
        """Add a new voice configuration"""
        self._config["voices"][agent_name] = {
            "file": file,
            "description": description,
            "instruct": instruct,
        }
        self.save()

    def get_ref_text(self, agent_name: str) -> str:
        """Generate reference text for voice cloning"""
        return f"Hello there! I'm {agent_name.capitalize()}, your AI assistant. What are we doing?"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
