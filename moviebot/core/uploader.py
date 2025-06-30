import os
import re
import json
import shutil
import asyncio
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from telegram import Update, constants
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from core.config import Config
from core.queue import add_to_queue
from core.utils.filelock import atomic_write_json
from core.utils.logger import get_logger

log = get_logger("📤 uploader")

MOVIE_EXTENSIONS = [".mp4", ".mkv"]
YOUTUBE_REGEX = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+", re.IGNORECASE)

# 🎬 Main handler for uploads
async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    user = message.from_user.full_name
    timestamp = int(datetime.now().timestamp())

    if message.document or message.video:
        file = message.document or message.video
        ext = Path(file.file_name).suffix.lower()

        if ext not in MOVIE_EXTENSIONS:
            await message.reply_text("❌ Unsupported format. Only .mp4 or .mkv are accepted.")
            return

        try:
            file_path = await download_file(file, Config.MOVIE_DIR)
            metadata = build_metadata(
                title=Path(file_path).stem,
                file_path=str(file_path),
                duration=getattr(file, 'duration', 0),
                file_type="upload",
                added_by=user,
                timestamp=timestamp
            )
            add_to_queue(**metadata)
            await message.reply_text(f"✅ *Uploaded & Queued:*\n`{metadata['title']}`", parse_mode=constants.ParseMode.MARKDOWN)
            log.info(f"📥 File uploaded by {user}: {file_path}")
        except Exception as e:
            log.error(f"❌ Upload failed: {e}")
            await message.reply_text("🚫 Failed to upload the file.")

    elif message.text and YOUTUBE_REGEX.match(message.text):
        url = message.text.strip()
        try:
            yt_meta = await download_youtube_video(url, Config.YOUTUBE_DIR)
            metadata = build_metadata(
                title=yt_meta["title"],
                file_path=yt_meta["filepath"],
                duration=yt_meta["duration"],
                file_type="youtube",
                added_by=user,
                timestamp=timestamp
            )
            add_to_queue(**metadata)
            await message.reply_text(f"📺 *YouTube Added to Queue:*\n`{metadata['title']}`", parse_mode=constants.ParseMode.MARKDOWN)
            log.info(f"🎞️ YouTube video queued by {user}: {metadata['title']}")
        except Exception as e:
            log.error(f"❌ YouTube download error: {e}")
            await message.reply_text("🚫 Failed to process YouTube link.")
    else:
        await message.reply_text("📩 Please send a valid movie file or YouTube link.")

# 🏷️ Metadata constructor
def build_metadata(title, file_path, duration, file_type, added_by, timestamp):
    return {
        "title": title,
        "file_path": file_path,
        "duration": duration,
        "type": file_type,
        "added_by": added_by,
        "timestamp": timestamp
    }

# 📁 File download
async def download_file(file_obj, destination_dir):
    safe_name = sanitize_filename(file_obj.file_name)
    unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    output_path = Path(destination_dir) / unique_name
    file = await file_obj.get_file()
    await file.download_to_drive(output_path)
    log.debug(f"⬇️ File saved to {output_path}")
    return output_path

# 📹 YouTube downloader via yt-dlp
async def download_youtube_video(url, destination_dir):
    output_template = f"{destination_dir}/%(title).200s.%(ext)s"
    cmd = [
        Config.YTDLP_PATH,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--write-info-json",
        "-o", output_template,
        url
    ]

    log.debug(f"🔗 Running yt-dlp: {url}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")

    downloaded_files = sorted(
        Path(destination_dir).glob("*.mp4"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

    if not downloaded_files:
        raise FileNotFoundError("No .mp4 file found after download.")

    latest_file = downloaded_files[0]
    info_json = latest_file.with_suffix(".info.json")

    if not info_json.exists():
        raise FileNotFoundError("Missing metadata (.info.json).")

    with open(info_json, "r", encoding="utf-8") as f:
        info = json.load(f)

    return {
        "title": info.get("title", latest_file.stem),
        "filepath": str(latest_file),
        "duration": int(info.get("duration", 0))
    }

# 🧼 Safe filenames
def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-_.() ]", "_", name)

# 🚀 Start bot
def run_uploader_bot():
    app = Application.builder().token(Config.TELEGRAM_UPLOAD_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_upload))
    log.info("📡 Uploader bot is online.")
    app.run_polling()

if __name__ == "__main__":
    run_uploader_bot()