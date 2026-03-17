"""
Push-to-talk STT daemon entry point.

Orchestrates the hotkey listener, audio recorder, transcriber,
and text injector into a cohesive push-to-talk experience.
"""

import argparse
import logging
import signal
import sys
import threading
from typing import Optional

from client.stt.config import PTTConfig
from client.stt.hotkey import HotkeyListener
from client.stt.injector import inject_text
from client.stt.recorder import AudioRecorder
from client.stt.transcriber import transcribe_audio

logger = logging.getLogger(__name__)


class PTTDaemon:
    """Main push-to-talk daemon that ties all components together.

    Args:
        config: PTTConfig with voice server and recording settings.
    """

    def __init__(self, config: PTTConfig) -> None:
        self.config = config
        self.recorder = AudioRecorder(
            sample_rate=config.audio_sample_rate,
            channels=config.audio_channels,
        )
        self._hotkey_listener: Optional[HotkeyListener] = None
        self._shutdown_event = threading.Event()

    def on_activate(self) -> None:
        """Called when the PTT hotkey is pressed — starts recording."""
        if not self.recorder.is_recording:
            logger.info("PTT activated — recording started")
            self.recorder.start_recording()

    def on_deactivate(self) -> None:
        """Called when the PTT hotkey is released — stops, transcribes, injects."""
        if not self.recorder.is_recording:
            return

        logger.info("PTT deactivated — processing audio")
        audio_data = self.recorder.stop_recording()

        if audio_data is None:
            logger.warning("No audio captured")
            return

        try:
            text = transcribe_audio(
                audio_data=audio_data,
                server_url=self.config.server_url,
                api_key=self.config.voice_server_api_key,
            )
            logger.info("Transcribed: %s", text[:80] if text else "(empty)")

            if text and text.strip():
                inject_text(text.strip(), method=self.config.injector_method)
                logger.info("Text injected successfully")
        except Exception:
            logger.exception("Transcription or injection failed")

    def run(self) -> None:
        """Start the PTT daemon and block until shutdown."""
        logger.info("Starting PTT daemon")
        logger.info("  Server: %s", self.config.server_url)
        logger.info("  Hotkey: %s", self.config.ptt_hotkey)
        logger.info("  Sample rate: %d Hz", self.config.audio_sample_rate)
        logger.info("  Injector: %s", self.config.injector_method)

        self._hotkey_listener = HotkeyListener(
            hotkey=self.config.ptt_hotkey,
            on_activate=self.on_activate,
            on_deactivate=self.on_deactivate,
        )
        self._hotkey_listener.start()

        print(f"PTT daemon running. Hold {self.config.ptt_hotkey} to record.")
        print("Press Ctrl+C to stop.")

        self._shutdown_event.wait()

    def shutdown(self) -> None:
        """Gracefully shut down the daemon."""
        logger.info("Shutting down PTT daemon")
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
        self._shutdown_event.set()


def main() -> None:
    """CLI entry point for the PTT daemon."""
    parser = argparse.ArgumentParser(
        description="Push-to-talk STT client for voice-to-text input",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        config = PTTConfig()
    except Exception as e:
        logger.error("Failed to load config: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        print("Set VOICE_SERVER_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    daemon = PTTDaemon(config=config)

    def signal_handler(signum: int, frame: object) -> None:
        logger.info("Received signal %d", signum)
        daemon.shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    daemon.run()


if __name__ == "__main__":
    main()
