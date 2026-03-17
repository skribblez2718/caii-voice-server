"""
Unit tests for client.stt.hotkey module (global hotkey listener)
"""

from unittest.mock import MagicMock, patch


class TestParseHotkey:
    """Tests for parse_hotkey - convert hotkey string to key components"""

    def test_parse_ctrl_alt_r(self) -> None:
        """Should parse 'ctrl+alt+r' into modifier and key components"""
        from client.stt.hotkey import parse_hotkey

        modifiers, key = parse_hotkey("ctrl+alt+r")
        assert "ctrl" in modifiers
        assert "alt" in modifiers
        assert key == "r"

    def test_parse_single_key(self) -> None:
        """Should parse 'f5' as no modifiers and key 'f5'"""
        from client.stt.hotkey import parse_hotkey

        modifiers, key = parse_hotkey("f5")
        assert modifiers == set()
        assert key == "f5"

    def test_parse_ctrl_shift_space(self) -> None:
        """Should parse 'ctrl+shift+space' correctly"""
        from client.stt.hotkey import parse_hotkey

        modifiers, key = parse_hotkey("ctrl+shift+space")
        assert "ctrl" in modifiers
        assert "shift" in modifiers
        assert key == "space"

    def test_parse_case_insensitive(self) -> None:
        """Should handle mixed case input"""
        from client.stt.hotkey import parse_hotkey

        modifiers, key = parse_hotkey("Ctrl+Alt+R")
        assert "ctrl" in modifiers
        assert "alt" in modifiers
        assert key == "r"


class TestHotkeyListener:
    """Tests for HotkeyListener - global keyboard event capture"""

    def test_listener_stores_callbacks(self) -> None:
        """Listener should store on_press and on_release callbacks"""
        from client.stt.hotkey import HotkeyListener

        on_press = MagicMock()
        on_release = MagicMock()

        listener = HotkeyListener(
            hotkey="ctrl+alt+r",
            on_activate=on_press,
            on_deactivate=on_release,
        )

        assert listener.on_activate is on_press
        assert listener.on_deactivate is on_release

    def test_listener_parses_hotkey(self) -> None:
        """Listener should parse the hotkey string on init"""
        from client.stt.hotkey import HotkeyListener

        listener = HotkeyListener(
            hotkey="ctrl+alt+r",
            on_activate=MagicMock(),
            on_deactivate=MagicMock(),
        )

        assert "ctrl" in listener.modifiers
        assert "alt" in listener.modifiers
        assert listener.key == "r"

    def test_listener_tracks_active_state(self) -> None:
        """Listener should track whether hotkey is currently active"""
        from client.stt.hotkey import HotkeyListener

        listener = HotkeyListener(
            hotkey="ctrl+alt+r",
            on_activate=MagicMock(),
            on_deactivate=MagicMock(),
        )

        assert listener.is_active is False

    @patch("client.stt.hotkey.PYNPUT_AVAILABLE", True)
    @patch("client.stt.hotkey.pynput_keyboard", create=True)
    def test_listener_start_creates_pynput_listener(self, mock_kb: MagicMock) -> None:
        """start() should create and start a pynput keyboard listener"""
        from client.stt.hotkey import HotkeyListener

        mock_listener_instance = MagicMock()
        mock_kb.Listener.return_value = mock_listener_instance

        listener = HotkeyListener(
            hotkey="ctrl+alt+r",
            on_activate=MagicMock(),
            on_deactivate=MagicMock(),
        )
        listener.start()

        mock_kb.Listener.assert_called_once()
        mock_listener_instance.start.assert_called_once()

    def test_listener_stop_sets_running_false(self) -> None:
        """stop() should set running to False"""
        from client.stt.hotkey import HotkeyListener

        listener = HotkeyListener(
            hotkey="ctrl+alt+r",
            on_activate=MagicMock(),
            on_deactivate=MagicMock(),
        )
        listener._running = True
        listener.stop()

        assert listener._running is False
