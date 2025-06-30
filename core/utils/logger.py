import logging
import os
import json
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# ==== CONFIGURATION ====
DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENABLE_JSON_LOGS = os.getenv("LOG_JSON", "0") == "1"
ENABLE_COLOR = os.getenv("LOG_COLOR", "1") == "1"

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / "moviebot.log"
ERROR_LOG_FILE = LOG_DIR / "moviebot.error.log"
MAX_LOG_SIZE_MB = 5
BACKUP_COUNT = 5

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ==== SETUP ====
LOG_DIR.mkdir(parents=True, exist_ok=True)
_logger_lock = threading.Lock()

# ANSI Color Codes
LEVEL_COLORS = {
    "DEBUG": "\033[94m",
    "INFO": "\033[92m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "CRITICAL": "\033[95m",
}
COLOR_RESET = "\033[0m"


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(log_record)


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        color = LEVEL_COLORS.get(record.levelname, "")
        reset = COLOR_RESET if color else ""
        base_msg = super().format(record)
        return f"{color}{base_msg}{reset}"


def _create_handler(file_path, level=logging.INFO, json_output=False):
    handler = RotatingFileHandler(
        file_path,
        maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    formatter = (
        JsonFormatter(datefmt=DATE_FORMAT)
        if json_output else
        logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def _create_console_handler(level=None, json_output=False):
    stream_handler = logging.StreamHandler()
    formatter = (
        JsonFormatter(datefmt=DATE_FORMAT)
        if json_output else
        ColoredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        if ENABLE_COLOR else
        logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    )
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level or DEFAULT_LOG_LEVEL)
    return stream_handler


def get_logger(name="moviebot", level=None, json_output=ENABLE_JSON_LOGS):
    with _logger_lock:
        logger = logging.getLogger(name)

        if logger.handlers:
            return logger  # Avoid adding handlers multiple times

        logger.setLevel(level or DEFAULT_LOG_LEVEL)

        # Handlers
        logger.addHandler(_create_handler(LOG_FILE, logging.INFO, json_output))
        logger.addHandler(_create_handler(ERROR_LOG_FILE, logging.ERROR, json_output))
        logger.addHandler(_create_console_handler(level, json_output))

        logger.propagate = False
        return logger


# CLI Diagnostics
if __name__ == "__main__":
    log = get_logger("diagnostic", level="DEBUG", json_output=False)

    log.debug("🐞 Debug message")
    log.info("ℹ️ Info message")
    log.warning("⚠️ Warning message")
    log.error("❌ Error message")
    log.critical("🔥 Critical message")
