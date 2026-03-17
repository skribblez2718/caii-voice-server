"""
Unit tests for client.stt.config module (PTT client configuration)
"""


class TestSTTClientConfig:
    """Tests for PTTConfig - push-to-talk client configuration"""

    def test_voice_server_protocol_default_returns_http(self) -> None:
        """voice_server_protocol should default to 'http'"""
        from client.stt.config import PTTConfig

        config = PTTConfig(voice_server_api_key="test-key")
        assert config.voice_server_protocol == "http"

    def test_voice_server_host_default_returns_localhost(self) -> None:
        """voice_server_host should default to 'localhost'"""
        from client.stt.config import PTTConfig

        config = PTTConfig(voice_server_api_key="test-key")
        assert config.voice_server_host == "localhost"

    def test_voice_server_port_default_returns_8001(self) -> None:
        """voice_server_port should default to 8001"""
        from client.stt.config import PTTConfig

        config = PTTConfig(voice_server_api_key="test-key")
        assert config.voice_server_port == 8001

    def test_ptt_hotkey_default_returns_ctrl_alt_r(self) -> None:
        """ptt_hotkey should default to 'ctrl+alt+r'"""
        from client.stt.config import PTTConfig

        config = PTTConfig(voice_server_api_key="test-key")
        assert config.ptt_hotkey == "ctrl+alt+r"

    def test_audio_sample_rate_default_returns_16000(self) -> None:
        """audio_sample_rate should default to 16000"""
        from client.stt.config import PTTConfig

        config = PTTConfig(voice_server_api_key="test-key")
        assert config.audio_sample_rate == 16000

    def test_audio_channels_default_returns_1(self) -> None:
        """audio_channels should default to 1"""
        from client.stt.config import PTTConfig

        config = PTTConfig(voice_server_api_key="test-key")
        assert config.audio_channels == 1

    def test_injector_method_default_returns_auto(self) -> None:
        """injector_method should default to 'auto'"""
        from client.stt.config import PTTConfig

        config = PTTConfig(voice_server_api_key="test-key")
        assert config.injector_method == "auto"

    def test_voice_server_api_key_from_env_overrides(self, monkeypatch) -> None:
        """voice_server_api_key should be loadable from VOICE_SERVER_API_KEY env var"""
        monkeypatch.setenv("VOICE_SERVER_API_KEY", "env-api-key")
        from importlib import reload

        import client.stt.config as config_module

        reload(config_module)
        config = config_module.PTTConfig()
        assert config.voice_server_api_key == "env-api-key"

    def test_server_url_computed_property(self) -> None:
        """server_url property should return 'protocol://host:port'"""
        from client.stt.config import PTTConfig

        config = PTTConfig(voice_server_api_key="test-key")
        assert config.server_url == "http://localhost:8001"
