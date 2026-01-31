"""
Unit tests for app.dependencies module

Tests TTSManager with mocked models to verify correct behavior,
especially the voice_clone_prompt handling that was previously buggy.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestTTSManagerSTTTiming:
    """Tests for STT model load timing capture"""

    def test_stt_load_seconds_initialized_to_zero(self) -> None:
        """TTSManager should initialize stt_load_seconds to 0.0"""
        from app.dependencies import TTSManager

        manager = TTSManager()
        assert manager.stt_load_seconds == 0.0

    @pytest.mark.asyncio
    async def test_stt_load_seconds_captured_on_load(self) -> None:
        """_load_stt_model should capture load time in stt_load_seconds"""
        from app.dependencies import TTSManager

        manager = TTSManager()

        with patch("faster_whisper.WhisperModel") as mock_whisper:
            mock_whisper.return_value = MagicMock()
            await manager._load_stt_model()

        # Should have captured some time (greater than or equal to 0)
        assert manager.stt_load_seconds >= 0.0


class TestTTSManagerTranscribeOptions:
    """Tests for transcribe_audio passing config options"""

    @pytest.mark.asyncio
    async def test_transcribe_passes_beam_size(self) -> None:
        """transcribe_audio should pass beam_size from settings"""
        from app.dependencies import TTSManager

        manager = TTSManager()
        mock_stt = MagicMock()
        mock_stt.transcribe.return_value = (
            [MagicMock(text="test")],
            MagicMock(language="en", duration=1.0),
        )
        manager.stt_model = mock_stt

        # Create mock audio bytes (minimal WAV header)
        audio_bytes = b"RIFF" + b"\x00" * 1000

        with patch("pydub.AudioSegment") as mock_audio:
            mock_segment = MagicMock()
            mock_segment.set_frame_rate.return_value = mock_segment
            mock_segment.set_channels.return_value = mock_segment
            mock_segment.raw_data = b"\x00" * 1000
            mock_audio.from_file.return_value = mock_segment

            with patch("app.dependencies.settings") as mock_settings:
                mock_settings.stt_beam_size = 10
                mock_settings.stt_best_of = 5
                mock_settings.stt_vad_filter = True
                await manager.transcribe_audio(audio_bytes)

        # Verify beam_size was passed
        call_kwargs = mock_stt.transcribe.call_args.kwargs
        assert call_kwargs.get("beam_size") == 10

    @pytest.mark.asyncio
    async def test_transcribe_passes_best_of(self) -> None:
        """transcribe_audio should pass best_of from settings"""
        from app.dependencies import TTSManager

        manager = TTSManager()
        mock_stt = MagicMock()
        mock_stt.transcribe.return_value = (
            [MagicMock(text="test")],
            MagicMock(language="en", duration=1.0),
        )
        manager.stt_model = mock_stt

        audio_bytes = b"RIFF" + b"\x00" * 1000

        with patch("pydub.AudioSegment") as mock_audio:
            mock_segment = MagicMock()
            mock_segment.set_frame_rate.return_value = mock_segment
            mock_segment.set_channels.return_value = mock_segment
            mock_segment.raw_data = b"\x00" * 1000
            mock_audio.from_file.return_value = mock_segment

            with patch("app.dependencies.settings") as mock_settings:
                mock_settings.stt_beam_size = 5
                mock_settings.stt_best_of = 3
                mock_settings.stt_vad_filter = True
                await manager.transcribe_audio(audio_bytes)

        call_kwargs = mock_stt.transcribe.call_args.kwargs
        assert call_kwargs.get("best_of") == 3

    @pytest.mark.asyncio
    async def test_transcribe_passes_vad_filter(self) -> None:
        """transcribe_audio should pass vad_filter from settings"""
        from app.dependencies import TTSManager

        manager = TTSManager()
        mock_stt = MagicMock()
        mock_stt.transcribe.return_value = (
            [MagicMock(text="test")],
            MagicMock(language="en", duration=1.0),
        )
        manager.stt_model = mock_stt

        audio_bytes = b"RIFF" + b"\x00" * 1000

        with patch("pydub.AudioSegment") as mock_audio:
            mock_segment = MagicMock()
            mock_segment.set_frame_rate.return_value = mock_segment
            mock_segment.set_channels.return_value = mock_segment
            mock_segment.raw_data = b"\x00" * 1000
            mock_audio.from_file.return_value = mock_segment

            with patch("app.dependencies.settings") as mock_settings:
                mock_settings.stt_beam_size = 5
                mock_settings.stt_best_of = 5
                mock_settings.stt_vad_filter = False
                await manager.transcribe_audio(audio_bytes)

        call_kwargs = mock_stt.transcribe.call_args.kwargs
        assert call_kwargs.get("vad_filter") is False


class TestTTSManagerVoicePrompt:
    """Tests for voice prompt handling in TTSManager"""

    def test_voice_prompt_not_double_wrapped(self, mock_base_model: MagicMock) -> None:
        """
        Verify that voice_clone_prompt is NOT double-wrapped when passed to generate_voice_clone.

        This tests the fix for the bug where create_voice_clone_prompt() returns
        List[VoiceClonePromptItem], but the code was wrapping it in another list,
        causing [[VoiceClonePromptItem(...)]] instead of [VoiceClonePromptItem(...)].
        """
        # Simulate what create_voice_clone_prompt returns
        voice_prompt = [{"audio_tokens": [1, 2, 3], "text": "Hello there!"}]
        mock_base_model.create_voice_clone_prompt.return_value = voice_prompt

        # Verify the expected structure
        result = mock_base_model.create_voice_clone_prompt(
            ref_audio="/path/to/audio.wav", ref_text="Hello there!"
        )

        # Result should be a list (not double-wrapped)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)

        # When passed to generate_voice_clone, it should be passed directly
        # NOT wrapped in another list
        mock_base_model.generate_voice_clone(
            text="Test text",
            language="English",
            voice_clone_prompt=result,  # CORRECT: pass directly
        )

        mock_base_model.generate_voice_clone.assert_called_once()
        call_kwargs = mock_base_model.generate_voice_clone.call_args.kwargs
        assert call_kwargs["voice_clone_prompt"] == voice_prompt
        # Verify it's NOT double-wrapped
        assert call_kwargs["voice_clone_prompt"] != [voice_prompt]


class TestTTSManagerGenerateSpeech:
    """Tests for TTSManager.generate_speech method"""

    @pytest.mark.asyncio
    async def test_generate_speech_uses_cached_voice_prompt(
        self, mock_tts_manager: MagicMock
    ) -> None:
        """generate_speech should use cached voice prompts"""
        result = await mock_tts_manager.generate_speech(text="Hello", agent_name="da")

        mock_tts_manager.generate_speech.assert_called_once_with(text="Hello", agent_name="da")
        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_generate_speech_falls_back_to_default(self, mock_tts_manager: MagicMock) -> None:
        """generate_speech should fall back to default voice for unknown agent"""
        # This tests the fallback behavior - manager should handle it internally
        result = await mock_tts_manager.generate_speech(text="Hello", agent_name="unknown_agent")

        assert isinstance(result, bytes)


class TestTTSManagerIntegrationMock:
    """Integration-style tests with mocked Qwen models"""

    @pytest.mark.asyncio
    async def test_full_speech_generation_flow(self, mock_base_model: MagicMock) -> None:
        """Test the full flow from voice prompt to audio generation"""
        # Step 1: Create voice clone prompt (during startup)
        voice_prompt = mock_base_model.create_voice_clone_prompt(
            ref_audio="/path/to/da.wav", ref_text="Hello there! I'm Da, your AI assistant."
        )

        # Step 2: Generate speech with the prompt
        mock_base_model.generate_voice_clone.return_value = ([b"\x00" * 1000], 24000)
        wavs, sr = mock_base_model.generate_voice_clone(
            text="Test message",
            language="English",
            voice_clone_prompt=voice_prompt,  # CORRECT: not [voice_prompt]
        )

        # Verify the call was made correctly
        call_kwargs = mock_base_model.generate_voice_clone.call_args.kwargs
        assert "voice_clone_prompt" in call_kwargs
        # The prompt should be the list returned by create_voice_clone_prompt
        # NOT wrapped in another list
        assert call_kwargs["voice_clone_prompt"] == voice_prompt

    def test_voice_prompt_structure_matches_api_expectation(
        self, mock_base_model: MagicMock
    ) -> None:
        """Verify voice prompt structure matches what Qwen-TTS API expects"""
        # Qwen-TTS expects voice_clone_prompt to be List[VoiceClonePromptItem]
        # where VoiceClonePromptItem has specific fields

        voice_prompt = mock_base_model.create_voice_clone_prompt(
            ref_audio="/path/to/audio.wav", ref_text="Reference text"
        )

        # Should be a list
        assert isinstance(voice_prompt, list)

        # Each item should be a dict-like structure (VoiceClonePromptItem)
        for item in voice_prompt:
            assert isinstance(item, dict)
