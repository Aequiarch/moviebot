import os
import time
import subprocess
from pathlib import Path
from core.utils.logger import get_logger

log = get_logger("📷 virtual-cam")

# 🎛️ Constants
V4L2_MODULE = "v4l2loopback"
DEFAULT_DEVICE = "/dev/video10"
MODULE_PARAMS = {
    "devices": 1,
    "video_nr": 10,
    "card_label": "MovieBotCam",
    "exclusive_caps": 1
}

class VirtualCamManager:
    def __init__(self, device_path=DEFAULT_DEVICE):
        self.device_path = device_path

    def is_module_loaded(self) -> bool:
        """Check if the v4l2loopback module is loaded."""
        result = subprocess.run(["lsmod"], capture_output=True, text=True)
        return V4L2_MODULE in result.stdout

    def load_module(self):
        """Load the v4l2loopback kernel module with specified parameters."""
        if self.is_module_loaded():
            log.info(f"✅ {V4L2_MODULE} already loaded.")
            return

        args = ["sudo", "modprobe", V4L2_MODULE]
        args += [f"{k}={v}" for k, v in MODULE_PARAMS.items()]

        log.debug(f"🔧 Loading module with: {' '.join(args)}")
        result = subprocess.run(args, capture_output=True, text=True)

        if result.returncode != 0:
            log.error(f"❌ Failed to load {V4L2_MODULE}: {result.stderr.strip()}")
            raise RuntimeError("Could not load v4l2loopback module.")
        log.info("🟢 v4l2loopback loaded successfully.")

    def unload_module(self):
        """Unload the v4l2loopback module."""
        if not self.is_module_loaded():
            log.info("ℹ️ v4l2loopback not loaded. Skipping unload.")
            return

        result = subprocess.run(["sudo", "modprobe", "-r", V4L2_MODULE], capture_output=True, text=True)

        if result.returncode != 0:
            log.warning(f"⚠️ Could not unload {V4L2_MODULE}: {result.stderr.strip()}")
        else:
            log.info("🧹 v4l2loopback module unloaded.")

    def wait_for_device(self, timeout=10) -> bool:
        """Wait for the virtual camera device to become available."""
        for i in range(timeout):
            if os.path.exists(self.device_path):
                log.info(f"🎥 Virtual camera is ready at {self.device_path}")
                return True
            log.debug(f"⏳ Waiting for {self.device_path} ({i+1}/{timeout})...")
            time.sleep(1)

        log.error(f"⛔ Device {self.device_path} not found after {timeout} seconds.")
        return False

    def get_active_virtual_cam(self) -> str | None:
        """Find the first active virtual loopback camera device."""
        if os.path.exists(self.device_path):
            return self.device_path

        for dev in sorted(Path("/dev").glob("video*")):
            if self._is_loopback_device(str(dev)):
                return str(dev)
        return None

    def _is_loopback_device(self, dev_path: str) -> bool:
        try:
            result = subprocess.run(
                ["v4l2-ctl", "--device", dev_path, "--all"],
                capture_output=True, text=True
            )
            output = result.stdout
            return "MovieBotCam" in output or "Loopback" in output
        except Exception as e:
            log.debug(f"⚠️ Could not verify loopback for {dev_path}: {e}")
            return False

    def setup(self):
        """Setup virtual camera device and verify readiness."""
        log.info("🔧 Setting up virtual camera...")
        self.load_module()
        if not self.wait_for_device():
            raise RuntimeError("❌ Virtual camera device failed to initialize.")
        log.info("✅ Virtual camera setup complete.")

    def cleanup(self):
        """Clean up virtual camera resources."""
        log.info("🧹 Cleaning up virtual camera...")
        self.unload_module()

# 🎯 Convenience Functions

def setup_virtual_camera():
    cam = VirtualCamManager()
    cam.setup()

def cleanup_camera():
    cam = VirtualCamManager()
    cam.cleanup()

def get_virtual_cam_device():
    cam = VirtualCamManager()
    return cam.get_active_virtual_cam()

# 🔍 CLI Debug/Test Mode
if __name__ == "__main__":
    try:
        setup_virtual_camera()
    except Exception as e:
        log.error(f"❌ VirtualCam init failed: {e}")
