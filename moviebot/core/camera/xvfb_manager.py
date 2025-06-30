import os
import subprocess
import signal
import time
import psutil
from pathlib import Path
from core.utils.logger import get_logger

log = get_logger("xvfb")

# Config
XVFB_DISPLAY = ":99"
XVFB_RESOLUTION = "1280x720x24"
XVFB_PID_FILE = Path("/tmp/moviebot_xvfb.pid")
XVFB_ENV = {"DISPLAY": XVFB_DISPLAY}
XVFB_CMD = ["Xvfb", XVFB_DISPLAY, "-screen", "0", XVFB_RESOLUTION]


class XvfbManager:
    def __init__(self):
        self.display = XVFB_DISPLAY
        self.resolution = XVFB_RESOLUTION
        self.pid_file = XVFB_PID_FILE
        self.cmd = XVFB_CMD

    def is_running(self) -> bool:
        """Check if Xvfb is currently running based on PID file."""
        if not self.pid_file.exists():
            return False
        try:
            pid = int(self.pid_file.read_text().strip())
            proc = psutil.Process(pid)
            return proc.is_running() and "Xvfb" in proc.name()
        except Exception as e:
            log.debug(f"Xvfb check failed: {e}")
            return False

    def start(self):
        """Start Xvfb if not running."""
        if self.is_running():
            log.info("🖥️ Xvfb is already running.")
            return

        try:
            log.info(f"🚀 Starting Xvfb on {self.display} with resolution {self.resolution}")
            proc = subprocess.Popen(self.cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.pid_file.write_text(str(proc.pid))
            time.sleep(1)
            if not self.is_running():
                raise RuntimeError("Xvfb failed to start.")
            log.info("✅ Xvfb started successfully.")
        except Exception as e:
            log.error(f"❌ Could not start Xvfb: {e}")
            raise

    def stop(self):
        """Stop the Xvfb process."""
        if not self.pid_file.exists():
            log.warning("⚠️ No PID file found. Xvfb may not be running.")
            return
        try:
            pid = int(self.pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            self.pid_file.unlink()
            log.info("🛑 Xvfb stopped cleanly.")
        except Exception as e:
            log.warning(f"⚠️ Failed to stop Xvfb: {e}")

    def restart(self):
        """Restart Xvfb cleanly."""
        log.info("🔄 Restarting Xvfb...")
        self.stop()
        self.start()

    def ensure_ready(self):
        """Ensure Xvfb is up and set DISPLAY env."""
        if not self.is_running():
            self.start()
        os.environ["DISPLAY"] = self.display
        log.info(f"🌐 Environment set: DISPLAY={self.display}")

    def get_status(self) -> str:
        """Return string status."""
        return "running" if self.is_running() else "stopped"

    def info(self):
        """Debug info about current state."""
        return {
            "display": self.display,
            "pid_file": str(self.pid_file),
            "running": self.is_running(),
            "env": f"DISPLAY={self.display}"
        }


# Global access methods
_manager = XvfbManager()

def start_xvfb():
    _manager.start()

def stop_xvfb():
    _manager.stop()

def restart_xvfb():
    _manager.restart()

def ensure_xvfb_ready():
    _manager.ensure_ready()

def is_running():
    return _manager.is_running()

def get_status():
    return _manager.get_status()


# CLI support
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Xvfb Manager for MovieBot")
    parser.add_argument("action", choices=["start", "stop", "restart", "status", "ensure"], help="Action to perform")
    args = parser.parse_args()

    if args.action == "start":
        start_xvfb()
    elif args.action == "stop":
        stop_xvfb()
    elif args.action == "restart":
        restart_xvfb()
    elif args.action == "ensure":
        ensure_xvfb_ready()
    elif args.action == "status":
        status = "✅ Running" if is_running() else "❌ Not Running"
        print(f"Xvfb status: {status}")
