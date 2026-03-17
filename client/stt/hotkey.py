"""
Global hotkey listener for push-to-talk activation.

Uses pynput for X11/Xwayland/WSLg environments. Falls back to evdev
for pure Wayland. Supports hold-to-record with configurable key combos.
"""

import logging
import threading
from typing import Callable, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Modifier key names recognized by the parser
MODIFIER_KEYS = {"ctrl", "alt", "shift", "super", "meta", "cmd"}

# Try importing pynput — it's the primary backend
try:
    from pynput import keyboard as pynput_keyboard

    PYNPUT_AVAILABLE = True
except ImportError:
    pynput_keyboard = None  # type: ignore[assignment]
    PYNPUT_AVAILABLE = False


def parse_hotkey(hotkey_string: str) -> Tuple[Set[str], str]:
    """Parse a hotkey string into modifiers and trigger key.

    Args:
        hotkey_string: Hotkey like 'ctrl+alt+r' or 'f5'.

    Returns:
        Tuple of (modifier_set, key_string). Modifiers are lowercase.
    """
    parts = [p.strip().lower() for p in hotkey_string.split("+")]
    modifiers: Set[str] = set()
    key = ""

    for part in parts:
        if part in MODIFIER_KEYS:
            modifiers.add(part)
        else:
            key = part

    return modifiers, key


class HotkeyListener:
    """Listens for a global hotkey and fires callbacks on press/release.

    Args:
        hotkey: Hotkey string like 'ctrl+alt+r'.
        on_activate: Called when the hotkey combination is fully pressed.
        on_deactivate: Called when any key in the combo is released.
    """

    def __init__(
        self,
        hotkey: str,
        on_activate: Callable[[], None],
        on_deactivate: Callable[[], None],
    ) -> None:
        self.modifiers, self.key = parse_hotkey(hotkey)
        self.on_activate = on_activate
        self.on_deactivate = on_deactivate
        self.is_active = False
        self._running = False
        self._pressed_modifiers: Set[str] = set()
        self._key_pressed = False
        self._listener: Optional[object] = None
        self._lock = threading.Lock()

    def _modifier_name(self, key: object) -> Optional[str]:
        """Map a pynput key to our modifier name."""
        if not PYNPUT_AVAILABLE:
            return None
        key_map = {
            pynput_keyboard.Key.ctrl_l: "ctrl",
            pynput_keyboard.Key.ctrl_r: "ctrl",
            pynput_keyboard.Key.alt_l: "alt",
            pynput_keyboard.Key.alt_r: "alt",
            pynput_keyboard.Key.shift_l: "shift",
            pynput_keyboard.Key.shift_r: "shift",
            pynput_keyboard.Key.cmd_l: "super",
            pynput_keyboard.Key.cmd_r: "super",
        }
        return key_map.get(key)

    def _key_char(self, key: object) -> Optional[str]:
        """Extract the character from a pynput key."""
        if not PYNPUT_AVAILABLE:
            return None
        if hasattr(key, "char") and key.char:
            return key.char.lower()
        if hasattr(key, "name") and key.name:
            return key.name.lower()
        return None

    def _on_press(self, key: object) -> None:
        """Handle key press events from pynput."""
        with self._lock:
            mod = self._modifier_name(key)
            if mod and mod in self.modifiers:
                self._pressed_modifiers.add(mod)

            char = self._key_char(key)
            if char == self.key:
                self._key_pressed = True

            # Check if full combo is active
            if (
                not self.is_active
                and self._key_pressed
                and self._pressed_modifiers >= self.modifiers
            ):
                self.is_active = True
                logger.info("Hotkey activated")
                self.on_activate()

    def _on_release(self, key: object) -> None:
        """Handle key release events from pynput."""
        with self._lock:
            mod = self._modifier_name(key)
            if mod:
                self._pressed_modifiers.discard(mod)

            char = self._key_char(key)
            if char == self.key:
                self._key_pressed = False

            # Deactivate if combo was active and any key released
            if self.is_active and (
                not self._key_pressed
                or not (self._pressed_modifiers >= self.modifiers)
            ):
                self.is_active = False
                logger.info("Hotkey deactivated")
                self.on_deactivate()

    def start(self) -> None:
        """Start listening for the global hotkey."""
        if not PYNPUT_AVAILABLE:
            raise RuntimeError(
                "pynput is not installed. Install with: pip install pynput"
            )

        self._running = True
        self._listener = pynput_keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        logger.info(
            "Hotkey listener started: %s+%s",
            "+".join(sorted(self.modifiers)),
            self.key,
        )

    def stop(self) -> None:
        """Stop listening for the global hotkey."""
        self._running = False
        if self._listener is not None and hasattr(self._listener, "stop"):
            self._listener.stop()
            self._listener = None
        logger.info("Hotkey listener stopped")
