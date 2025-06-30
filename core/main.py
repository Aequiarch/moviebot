import threading
import asyncio
import signal
import time
import sys
from functools import partial

from core import config
from core import logger
from core import uploader
from core import player
from core import controller
from core import discordbot
from core import telegramcontrol
from core.camera import virtual_cam, xvfb_manager

# Global state
threads = {}
running = True
thread_targets = {}
restart_counters = {}

MAX_RESTART_ATTEMPTS = 5
RESTART_BACKOFF = 5  # seconds


def start_thread(name, target, daemon=True):
    def wrapper():
        try:
            logger.log_debug(f"🔧 Thread '{name}' executing target function...")
            target()
        except Exception as e:
            logger.log_error(f"💥 Thread '{name}' crashed: {e}")

    if name in threads and threads[name].is_alive():
        logger.log_warning(f"⚠️ Attempted to start thread '{name}' but it's already running.")
        return

    t = threading.Thread(target=wrapper, daemon=daemon)
    threads[name] = t
    thread_targets[name] = target
    restart_counters.setdefault(name, 0)
    t.start()
    logger.log_info(f"🧵 Started thread: {name}")


def start_async_thread(name, coroutine):
    def runner():
        try:
            asyncio.run(coroutine())
        except Exception as e:
            logger.log_error(f"⚠️ Async thread '{name}' failed: {e}")

    start_thread(name, runner)


def init_all():
    logger.log_info("🚀 Initializing MovieBot components...")
    config.validate_all()
    xvfb_manager.start_display()
    virtual_cam.init_virtual_camera()

    start_thread("Player", player.run)
    start_thread("Uploader", uploader.run)
    start_thread("Controller", controller.run)
    start_async_thread("DiscordBot", discordbot.run)
    start_async_thread("TelegramControl", telegramcontrol.run)


def monitor():
    logger.log_info("🩺 Monitor thread active. Watching services...")
    while running:
        for name, thread in list(threads.items()):
            if not thread.is_alive():
                logger.log_warning(f"⚠️ Thread '{name}' is no longer alive.")
                attempts = restart_counters.get(name, 0)
                if attempts >= MAX_RESTART_ATTEMPTS:
                    logger.log_critical(f"❌ Max restart attempts reached for '{name}'. Skipping restart.")
                    continue

                logger.log_info(f"🔄 Attempting to restart '{name}' (attempt {attempts + 1})...")
                time.sleep(RESTART_BACKOFF)
                restart_counters[name] += 1
                try:
                    start_thread(name, thread_targets[name])
                except Exception as e:
                    logger.log_error(f"❌ Failed to restart '{name}': {e}")
        time.sleep(3)


def shutdown(signum=None, frame=None):
    global running
    logger.log_info("📴 Initiating graceful shutdown of MovieBot...")
    running = False

    try:
        player.stop()
    except Exception as e:
        logger.log_warning(f"Player stop failed: {e}")

    try:
        virtual_cam.cleanup_virtual_camera()
    except Exception as e:
        logger.log_warning(f"VirtualCam cleanup failed: {e}")

    try:
        xvfb_manager.stop_display()
    except Exception as e:
        logger.log_warning(f"Xvfb stop failed: {e}")

    logger.log_info("✅ Shutdown complete.")
    sys.exit(0)


def reload_threads():
    logger.log_info("🔁 Reloading all MovieBot threads...")
    for name, target in thread_targets.items():
        try:
            if name in threads and threads[name].is_alive():
                continue
            start_thread(name, target)
        except Exception as e:
            logger.log_error(f"🔁 Reload failed for {name}: {e}")


def list_thread_status():
    logger.log_info("📋 Listing thread status:")
    for name, thread in threads.items():
        logger.log_info(f" - {name}: {'✅ Alive' if thread.is_alive() else '❌ Dead'}")


def manual_restart(name: str):
    if name not in thread_targets:
        logger.log_error(f"🔍 No such thread to restart: {name}")
        return
    try:
        if threads.get(name) and threads[name].is_alive():
            logger.log_info(f"🔄 Stopping running thread: {name}")
            # No way to truly stop a Python thread; log and restart
        logger.log_info(f"🔄 Restarting thread: {name}")
        start_thread(name, thread_targets[name])
    except Exception as e:
        logger.log_error(f"❌ Failed manual restart for {name}: {e}")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        init_all()
        monitor()
    except Exception as e:
        logger.log_critical(f"🔥 Fatal error in main loop: {e}")
        shutdown()
