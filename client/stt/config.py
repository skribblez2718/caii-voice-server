"""
Configuration module for the push-to-talk (PTT) STT client.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PTTConfig(BaseSettings):
    """Push-to-talk client configuration loaded from environment variables.

    All fields can be overridden via environment variables. The
    voice_server_api_key field is required and reads from the
    VOICE_SERVER_API_KEY environment variable when not supplied directly.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    voice_server_protocol: str = Field(
        default="http",
        description="Protocol used to connect to the voice server (http or https).",
    )
    voice_server_host: str = Field(
        default="localhost",
        description="Hostname of the voice server.",
    )
    voice_server_port: int = Field(
        default=8001,
        description="Port of the voice server.",
    )
    voice_server_api_key: str = Field(
        description="API key for authenticating with the voice server. "
        "Reads from VOICE_SERVER_API_KEY environment variable.",
    )
    ptt_hotkey: str = Field(
        default="ctrl+alt+r",
        description="Keyboard shortcut that activates push-to-talk recording.",
    )
    audio_sample_rate: int = Field(
        default=16000,
        description="Audio sample rate in Hz for recording.",
    )
    audio_channels: int = Field(
        default=1,
        description="Number of audio channels (1 = mono, 2 = stereo).",
    )
    injector_method: str = Field(
        default="auto",
        description="Method used to inject transcribed text into the active application.",
    )

    @property
    def server_url(self) -> str:
        """Construct the full voice server base URL.

        Returns:
            Full URL string in the form 'protocol://host:port'.
        """
        return f"{self.voice_server_protocol}://{self.voice_server_host}:{self.voice_server_port}"
