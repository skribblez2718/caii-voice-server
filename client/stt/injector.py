"""
Text injection module for inserting transcribed text into the active terminal.

Detects the display server (X11/Wayland) and uses the appropriate tool:
- X11: xdotool type --clearmodifiers
- Wayland: wtype
"""

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def detect_display_server() -> str:
    """Detect the current display server.

    Returns:
        'wayland', 'x11', or 'unknown'.
    """
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def inject_text(text: str, method: str = "auto") -> None:
    """Type text into the currently focused terminal window.

    Args:
        text: The text to inject.
        method: Injection method — 'auto', 'xdotool', or 'wtype'.

    Raises:
        RuntimeError: If no display server is detected with method='auto'.
        subprocess.CalledProcessError: If the injection command fails.
    """
    if not text:
        return

    if method == "auto":
        display = detect_display_server()
        if display == "x11":
            method = "xdotool"
        elif display == "wayland":
            method = "wtype"
        else:
            raise RuntimeError(
                "No display server detected. Set DISPLAY (X11) or "
                "WAYLAND_DISPLAY (Wayland), or specify method explicitly."
            )

    if method == "xdotool":
        cmd = ["xdotool", "type", "--clearmodifiers", "--delay", "0", text]
    elif method == "wtype":
        cmd = ["wtype", text]
    else:
        raise ValueError(f"Unknown injection method: {method}")

    logger.info("Injecting text via %s (%d chars)", method, len(text))
    subprocess.run(cmd, check=True)
