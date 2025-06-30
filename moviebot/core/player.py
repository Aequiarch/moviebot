import os
import subprocess
import threading
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List

from core.config import config
from core.utils.filelock import FileLock

log = logging.getLogger("🎬 MoviePlayer")
log.setLevel(logging.DEBUG)
fh = logging.FileHandler(config.LOG_DIR / "player.log")
fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
log.addHandler(fh)


class MoviePlayer:
    def __init__(self):
        self.now_playing = config.NOW_PLAYING_FILE
        self.playlist = config.PLAYLIST_FILE
        self.control = config.CONTROL_FILE
        self.ffmpeg_path = config.FFMPEG_PATH
        self.virtual_cam = "/dev/video0"
        self.running = False
        self.process: Optional[subprocess.Popen] = None
        self.retry_limit = 3

    def get_next_video(self) -> Tuple[Optional[dict], Optional[List[dict]]]:
        with FileLock(str(self.playlist)):
            if not self.playlist.exists():
                return None, None
            try:
                with open(self.playlist, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not data:
                    return None, data
                return data.pop(0), data
            except json.JSONDecodeError:
                log.error("💥 Playlist file is corrupted.")
                return None, []

    def write_updated_playlist(self, updated: List[dict]):
        with FileLock(str(self.playlist)):
            with open(self.playlist, "w", encoding="utf-8") as f:
                json.dump(updated, f, indent=2)

    def update_now_playing(self, metadata: dict):
        with FileLock(str(self.now_playing)):
            with open(self.now_playing, "w", encoding="utf-8") as f:
                f.write(f"{metadata['file_path']}|{int(time.time())}")
        log.info(f"🎞️ Now playing: {metadata.get('title', 'Unknown Title')}")

    def clear_now_playing(self):
        with FileLock(str(self.now_playing)):
            with open(self.now_playing, "w", encoding="utf-8") as f:
                f.write("")
        log.info("🧹 Cleared now_playing.txt")

    def launch_ffmpeg(self, file_path: str) -> subprocess.Popen:
        cmd = [
            self.ffmpeg_path, "-re", "-i", file_path,
            "-map", "0:v:0", "-f", "v4l2", self.virtual_cam
        ]
        log.info(f"📽️ Launching FFmpeg: {' '.join(cmd)}")
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def should_skip(self) -> bool:
        try:
            with FileLock(str(self.control)):
                if not self.control.exists():
                    return False
                with open(self.control, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("skip", False)
        except Exception as e:
            log.error(f"🚫 Failed to read control file: {e}")
            return False

    def reset_controls(self):
        try:
            with FileLock(str(self.control)):
                with open(self.control, "w", encoding="utf-8") as f:
                    json.dump({}, f)
            log.info("🔄 Reset control.json")
        except Exception as e:
            log.error(f"⚠️ Reset control file failed: {e}")

    def play_video(self, video: dict, updated_playlist: List[dict]):
        file_path = video.get("file_path")
        if not file_path or not Path(file_path).exists():
            log.warning(f"❌ File not found: {file_path}")
            self.write_updated_playlist(updated_playlist)
            return

        self.update_now_playing(video)
        self.process = self.launch_ffmpeg(file_path)
        start_time = time.time()
        duration = video.get("duration", 0)
        max_play = duration if duration > 0 else 3600

        log.info(f"▶️ Streaming for {max_play}s")
        while time.time() - start_time < max_play:
            if self.should_skip():
                log.info("⏭️ Skip command received")
                self.reset_controls()
                break
            if self.process.poll() is not None:
                log.warning("⚠️ FFmpeg exited early")
                break
            time.sleep(1)

        if self.process and self.process.poll() is None:
            self.process.terminate()
            log.info("⛔ FFmpeg terminated")

        self.clear_now_playing()
        self.write_updated_playlist(updated_playlist)
        time.sleep(1)

    def play_loop(self):
        self.running = True
        log.info("🔁 Entering playback loop")
        while self.running:
            retries = 0
            next_video, updated_playlist = self.get_next_video()

            if not next_video:
                log.info("⏳ Playlist empty. Sleeping 10s")
                time.sleep(10)
                continue

            while retries < self.retry_limit:
                try:
                    self.play_video(next_video, updated_playlist)
                    break
                except Exception as e:
                    retries += 1
                    log.error(f"❌ Retry {retries} failed: {e}")
                    time.sleep(2)

            if retries >= self.retry_limit:
                log.error("🚫 Video failed after max retries. Skipping.")
                self.clear_now_playing()
                self.write_updated_playlist(updated_playlist)

    def stop(self):
        self.running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
            log.info("🛑 FFmpeg stopped")


def run_player():
    log.info("🎬 MoviePlayer launched")
    player = MoviePlayer()
    try:
        player.play_loop()
    except KeyboardInterrupt:
        player.stop()


if __name__ == "__main__":
    run_player()
