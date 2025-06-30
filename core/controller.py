import json
import time
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from core.utils.logger import get_logger
from core.utils.filelock import read_locked_json, write_locked_json
from core.queue import get_next_item, set_now_playing
from core.player import FFmpegPlayer

CONTROL_FILE = Path("control.json")
VALID_COMMANDS = {"pause", "resume", "skip", "stop", "reload"}

log = get_logger("controller")


class ControlManager:
    def __init__(self, check_interval: int = 1):
        self.interval = check_interval
        self.last_request_ids: Dict[str, Optional[str]] = {}
        self.player = FFmpegPlayer()
        self.paused = False
        self.running = True
        self.command_handlers: Dict[str, Callable[[str], None]] = {
            "pause": self._handle_pause,
            "resume": self._handle_resume,
            "skip": self._handle_skip,
            "stop": self._handle_stop,
            "reload": self._handle_reload
        }
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)

    def start(self):
        """Starts the control manager loop in a background thread."""
        log.info("🎛️ ControlManager thread started.")
        self.thread.start()

    def stop(self):
        """Stops the control loop."""
        self.running = False
        log.info("🛑 ControlManager thread stopping...")

    def _watch_loop(self):
        """Main loop that watches control.json for new commands."""
        while self.running:
            try:
                self._check_for_new_command()
            except Exception as e:
                log.exception(f"⚠️ Exception in controller loop: {e}")
            time.sleep(self.interval)

    def _check_for_new_command(self):
        """Check control.json for any new or unhandled commands."""
        if not CONTROL_FILE.exists():
            return

        command_data = read_locked_json(CONTROL_FILE)
        if not isinstance(command_data, dict):
            log.warning("⚠️ Invalid format in control.json.")
            return

        for command, payload in command_data.items():
            if command not in VALID_COMMANDS:
                log.warning(f"❌ Invalid command: {command}")
                continue

            request_id = payload.get("id")
            user = payload.get("user", "Unknown")

            if not request_id:
                log.warning(f"⚠️ Missing request ID for {command}. Skipping.")
                continue

            if self._is_duplicate(command, request_id):
                log.debug(f"🔁 Duplicate command ignored: {command} (ID {request_id})")
                continue

            log.info(f"📡 Received command: {command.upper()} from {user}")
            self.last_request_ids[command] = request_id
            self._apply_command(command, user)

    def _is_duplicate(self, command: str, request_id: str) -> bool:
        """Checks if a command was already processed based on its request ID."""
        return self.last_request_ids.get(command) == request_id

    def _apply_command(self, command: str, user: str):
        """Executes the given command."""
        handler = self.command_handlers.get(command)
        if handler:
            handler(user)
        else:
            log.error(f"No handler for command: {command}")

    def _handle_pause(self, user: str):
        if self.paused:
            log.info("⏸️ Already paused. Ignoring.")
            return
        log.info(f"⏸️ Playback paused by {user}.")
        self.paused = True
        self.player.stop_stream()

    def _handle_resume(self, user: str):
        if not self.paused:
            log.info("▶️ Already playing. Ignoring resume.")
            return
        log.info(f"▶️ Playback resumed by {user}.")
        self.paused = False
        self.player.run_once()

    def _handle_skip(self, user: str):
        log.info(f"⏭️ Skip command issued by {user}.")
        self.paused = False
        self.player.stop_stream()

        next_video = get_next_item()
        if next_video:
            log.info(f"📀 Next video queued: {next_video.get('title', 'Unknown')} by {user}")
            set_now_playing(next_video)
            self.player.run_once()
        else:
            log.warning("⚠️ Queue is empty. No next video to play.")

    def _handle_stop(self, user: str):
        log.info(f"🛑 Playback stopped by {user}.")
        self.paused = False
        self.player.stop_stream()

    def _handle_reload(self, user: str):
        log.info(f"🔁 Reloading configuration at request of {user}.")
        # Placeholder: Hook into config reload method if needed

    def reset_state(self):
        """Resets control manager to default state."""
        self.last_request_ids.clear()
        self.paused = False

    def force_command(self, command: str):
        """Forcefully applies a command without checking request ID."""
        if command in VALID_COMMANDS:
            log.warning(f"⚠️ Forcibly applying command: {command}")
            self._apply_command(command, "System")
        else:
            log.error(f"Invalid forced command: {command}")

    def debug_status(self) -> Dict[str, Any]:
        """Returns internal state for debugging purposes."""
        return {
            "paused": self.paused,
            "last_requests": self.last_request_ids,
            "player_status": self.player.status()
        }


# Optional test runner
if __name__ == "__main__":
    controller = ControlManager()
    try:
        controller.start()
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        controller.stop()
