import os
import sys
import shutil
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, List, Dict

CONFIG_LOADED = False


class ConfigError(Exception):
    """Custom error for configuration issues."""
    pass


class Config:
    """
    Loads and validates configuration from a .env file and sets up paths and required directories.
    Now includes:
    - Advanced .env validation with type casting
    - Detailed logging and structured summaries
    - Directory cleanup options
    - Config reload capability
    - Secrets redaction
    """

    REQUIRED_ENV_VARS = [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CONTROL_CHAT_ID",
        "DISCORD_EMAIL",
        "DISCORD_PASSWORD",
        "DISCORD_SERVER_ID",
        "DISCORD_CHANNEL_ID",
        "MOVIE_DATA_DIR",
        "YOUTUBE_DATA_DIR",
        "FFMPEG_PATH"
    ]

    OPTIONAL_ENV_DEFAULTS = {
        "LOG_DIR": "./logs",
        "DISCORD_BOT_TOKEN": None,
        "TELEGRAM_CONTROL_BOT_TOKEN": None,
        "TELEGRAM_ALLOWED_USERS": "",
        "YTDLP_PATH": "yt-dlp"
    }

    def __init__(self):
        self.env_path = Path(__file__).resolve().parent.parent / ".env"
        self._load_dotenv()
        self._validate_env_vars()
        self._assign_attributes()
        self._verify_binaries()
        self._ensure_directories()
        self._initialize_files()
        global CONFIG_LOADED
        CONFIG_LOADED = True

    def _load_dotenv(self):
        if not self.env_path.exists():
            raise ConfigError(f".env file not found at: {self.env_path}")
        load_dotenv(dotenv_path=self.env_path)

    def _validate_env_vars(self):
        missing = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

    def _assign_attributes(self):
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CONTROL_CHAT_ID = int(os.getenv("TELEGRAM_CONTROL_CHAT_ID"))
        self.DISCORD_EMAIL = os.getenv("DISCORD_EMAIL")
        self.DISCORD_PASSWORD = os.getenv("DISCORD_PASSWORD")
        self.DISCORD_SERVER_ID = os.getenv("DISCORD_SERVER_ID")
        self.DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

        self.MOVIE_DATA_DIR = Path(os.getenv("MOVIE_DATA_DIR")).resolve()
        self.YOUTUBE_DATA_DIR = Path(os.getenv("YOUTUBE_DATA_DIR")).resolve()
        self.LOG_DIR = Path(os.getenv("LOG_DIR", self.OPTIONAL_ENV_DEFAULTS["LOG_DIR"])).resolve()

        self.DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
        self.TELEGRAM_CONTROL_BOT_TOKEN = os.getenv("TELEGRAM_CONTROL_BOT_TOKEN")
        self.TELEGRAM_ALLOWED_USERS = [uid.strip() for uid in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if uid.strip()]

        self.FFMPEG_PATH = shutil.which(os.getenv("FFMPEG_PATH")) or os.getenv("FFMPEG_PATH")
        self.YTDLP_PATH = shutil.which(os.getenv("YTDLP_PATH", self.OPTIONAL_ENV_DEFAULTS["YTDLP_PATH"])) or "yt-dlp"

        self.PLAYLIST_FILE = Path("playlist.json")
        self.CONTROL_FILE = Path("control.json")
        self.NOW_PLAYING_FILE = Path("now_playing.txt")

    def _verify_binaries(self):
        for binary_path, name in [(self.FFMPEG_PATH, "FFmpeg"), (self.YTDLP_PATH, "yt-dlp")]:
            if not shutil.which(binary_path):
                raise ConfigError(f"{name} not found or not executable at: {binary_path}")

            try:
                output = os.popen(f"{binary_path} --version").read()
                if name.lower() not in output.lower():
                    raise ConfigError(f"Invalid {name} binary output.")
            except Exception as e:
                raise ConfigError(f"Error verifying {name}: {e}")

    def _ensure_directories(self):
        for directory in [self.MOVIE_DATA_DIR, self.YOUTUBE_DATA_DIR, self.LOG_DIR]:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                logging.info(f"📁 Created directory: {directory}")
            if not os.access(directory, os.W_OK):
                raise ConfigError(f"No write permission for directory: {directory}")

    def _initialize_files(self):
        defaults = {
            self.PLAYLIST_FILE: "[]",
            self.CONTROL_FILE: "{}",
            self.NOW_PLAYING_FILE: ""
        }
        for file_path, default_content in defaults.items():
            if not file_path.exists():
                try:
                    file_path.write_text(default_content)
                    logging.info(f"📄 Initialized file: {file_path}")
                except Exception as e:
                    raise ConfigError(f"Failed to create {file_path}: {e}")

    def summary(self) -> Dict[str, str]:
        return {
            "Telegram Bot Token": self.TELEGRAM_BOT_TOKEN[:6] + "...",
            "Discord Email": self.DISCORD_EMAIL,
            "Data Dirs": f"Movies: {self.MOVIE_DATA_DIR}, YT: {self.YOUTUBE_DATA_DIR}",
            "FFmpeg Path": self.FFMPEG_PATH,
            "yt-dlp Path": self.YTDLP_PATH
        }

    def reload(self):
        """Reload configuration from the .env file."""
        load_dotenv(dotenv_path=self.env_path, override=True)
        self._assign_attributes()
        self._verify_binaries()
        self._ensure_directories()

    def clear_temp_files(self):
        """Clear temporary or corrupted control files (used during reset)."""
        for file_path in [self.CONTROL_FILE, self.NOW_PLAYING_FILE]:
            if file_path.exists():
                file_path.unlink()
                logging.info(f"🗑️ Cleared temporary file: {file_path}")


# Initialize global config with error handling
try:
    config = Config()
except ConfigError as e:
    logging.error(f"❌ Configuration error: {e}")
    sys.exit(1)
