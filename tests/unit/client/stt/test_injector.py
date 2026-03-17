"""
Unit tests for client.stt.injector module (text injection into terminals)
"""

from unittest.mock import MagicMock, patch


class TestDetectDisplayServer:
    """Tests for detect_display_server - determine X11, Wayland, or unknown"""

    @patch.dict("os.environ", {"WAYLAND_DISPLAY": "wayland-0"}, clear=False)
    def test_detect_wayland_when_wayland_display_set(self) -> None:
        """Should return 'wayland' when WAYLAND_DISPLAY is set"""
        from client.stt.injector import detect_display_server

        result = detect_display_server()
        assert result == "wayland"

    @patch.dict("os.environ", {"DISPLAY": ":0"}, clear=False)
    @patch.dict("os.environ", {}, clear=False)
    def test_detect_x11_when_display_set(self) -> None:
        """Should return 'x11' when DISPLAY is set and WAYLAND_DISPLAY is not"""
        import os

        from client.stt.injector import detect_display_server

        os.environ.pop("WAYLAND_DISPLAY", None)
        result = detect_display_server()
        assert result == "x11"

    @patch.dict("os.environ", {}, clear=True)
    def test_detect_unknown_when_no_display_vars(self) -> None:
        """Should return 'unknown' when neither DISPLAY nor WAYLAND_DISPLAY set"""
        from client.stt.injector import detect_display_server

        result = detect_display_server()
        assert result == "unknown"


class TestInjectText:
    """Tests for inject_text - type text into active terminal"""

    @patch("client.stt.injector.subprocess.run")
    @patch("client.stt.injector.detect_display_server", return_value="x11")
    def test_inject_text_x11_uses_xdotool(
        self, mock_detect: MagicMock, mock_run: MagicMock
    ) -> None:
        """inject_text on X11 should call xdotool type with --clearmodifiers"""
        from client.stt.injector import inject_text

        mock_run.return_value = MagicMock(returncode=0)
        inject_text("hello world", method="auto")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "xdotool"
        assert "type" in cmd
        assert "--clearmodifiers" in cmd
        assert "hello world" in cmd

    @patch("client.stt.injector.subprocess.run")
    @patch("client.stt.injector.detect_display_server", return_value="wayland")
    def test_inject_text_wayland_uses_wtype(
        self, mock_detect: MagicMock, mock_run: MagicMock
    ) -> None:
        """inject_text on Wayland should call wtype"""
        from client.stt.injector import inject_text

        mock_run.return_value = MagicMock(returncode=0)
        inject_text("hello world", method="auto")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "wtype"
        assert "hello world" in cmd

    @patch("client.stt.injector.subprocess.run")
    def test_inject_text_explicit_xdotool_method(self, mock_run: MagicMock) -> None:
        """inject_text with method='xdotool' should use xdotool regardless of display"""
        from client.stt.injector import inject_text

        mock_run.return_value = MagicMock(returncode=0)
        inject_text("test text", method="xdotool")

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "xdotool"

    @patch("client.stt.injector.subprocess.run")
    def test_inject_text_explicit_wtype_method(self, mock_run: MagicMock) -> None:
        """inject_text with method='wtype' should use wtype regardless of display"""
        from client.stt.injector import inject_text

        mock_run.return_value = MagicMock(returncode=0)
        inject_text("test text", method="wtype")

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "wtype"

    @patch("client.stt.injector.subprocess.run")
    @patch("client.stt.injector.detect_display_server", return_value="unknown")
    def test_inject_text_unknown_display_raises(
        self, mock_detect: MagicMock, mock_run: MagicMock
    ) -> None:
        """inject_text with unknown display and auto method should raise RuntimeError"""
        import pytest

        from client.stt.injector import inject_text

        with pytest.raises(RuntimeError, match="No display server detected"):
            inject_text("test", method="auto")

    @patch("client.stt.injector.subprocess.run")
    def test_inject_text_escapes_empty_string(self, mock_run: MagicMock) -> None:
        """inject_text with empty string should not call subprocess"""
        from client.stt.injector import inject_text

        inject_text("", method="xdotool")
        mock_run.assert_not_called()
