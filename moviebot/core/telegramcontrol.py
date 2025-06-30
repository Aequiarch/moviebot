import uuid
from pathlib import Path

from telegram import Update, constants
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from core.config import Config
from core.utils.logger import get_logger
from core.utils.filelock import write_locked_json
from core.queue import get_now_playing, get_queue

log = get_logger("📱 telegram-control")

# 📁 Paths and Authorization
CONTROL_FILE = Path("control.json")
WHITELIST_USERS = set(Config.TELEGRAM_ALLOWED_USERS.split(",")) if Config.TELEGRAM_ALLOWED_USERS else set()

# 🔐 Utility: Check if a user is authorized
def is_authorized(user_id: int) -> bool:
    return not WHITELIST_USERS or str(user_id) in WHITELIST_USERS

# 🔣 Utility: Escape special characters for Telegram MarkdownV2
def markdown_escape(text: str) -> str:
    escape_chars = r"\\_*[]()~`>#+-=|{}.!"
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text

# 🧠 Utility: Response messages for each control command
def build_response_message(command: str) -> str:
    return {
        "pause": "⏸️ Movie playback paused.",
        "resume": "▶️ Playback resumed.",
        "skip": "⏭️ Skipped to next video in queue.",
        "stop": "⏹️ Playback stopped.",
    }.get(command, "✅ Command sent successfully.")

# 📤 Send control signal to MovieBot core
async def send_control_signal(command: str, user: str):
    signal = {
        command: {
            "id": str(uuid.uuid4()),
            "user": user
        }
    }
    write_locked_json(CONTROL_FILE, signal)
    log.info(f"📡 Control issued: {command} by {user}")

# 🧩 General control handler for shared logic
async def handle_control_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    user = update.effective_user
    username = user.username or str(user.id)

    if not is_authorized(user.id):
        log.warning(f"🚫 Unauthorized access attempt by user ID {user.id}")
        await update.message.reply_text("🚫 You are not authorized to control MovieBot.")
        return

    await send_control_signal(command, username)
    await update.message.reply_text(build_response_message(command))

# 🎮 Command Handlers
async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_control_command(update, context, "pause")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_control_command(update, context, "resume")

async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_control_command(update, context, "skip")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_control_command(update, context, "stop")

# 🎥 Show current playing item
async def nowplaying(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = get_now_playing()

    if not now:
        await update.message.reply_text("🎬 No movie is currently playing.")
        return

    title = markdown_escape(now['title'])
    duration = f"{now['duration']}s"
    source = markdown_escape(now['type'])
    added_by = markdown_escape(now['added_by'])

    msg = (
        "*🎥 Now Playing:*\n"
        f"• *Title:* `{title}`\n"
        f"• *Duration:* `{duration}`\n"
        f"• *Source:* `{source}`\n"
        f"• *Added by:* `{added_by}`"
    )
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN_V2)

# 📋 Show the upcoming queue (limited to 10 entries)
async def queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = get_queue()

    if not q:
        await update.message.reply_text("📭 The queue is currently empty.")
        return

    msg = ["*🎞️ Upcoming Queue:*\n"]
    for i, item in enumerate(q[:10], start=1):
        title = markdown_escape(item['title'])
        added_by = markdown_escape(item['added_by'])
        duration = item.get('duration', 0)
        msg.append(f"{i}. `{title}` – {duration}s by `{added_by}`")

    await update.message.reply_text("\n".join(msg), parse_mode=constants.ParseMode.MARKDOWN_V2)

# 🧾 Status = now playing + queue
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await nowplaying(update, context)
    await queue(update, context)

# 📖 Help command with Markdown formatting and emojis
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*🎮 MovieBot Control Commands:*\n"
        "\n"
        "`/pause` – ⏸️ Pause playback\n"
        "`/resume` – ▶️ Resume playback\n"
        "`/skip` – ⏭️ Skip to next\n"
        "`/stop` – ⏹️ Stop playback\n"
        "`/nowplaying` – 🎬 Show current video\n"
        "`/queue` – 📝 Show next 10 queued\n"
        "`/status` – 📊 Playback + Queue info\n"
        "`/help` – ❓ This help message"
    )
    await update.message.reply_text(help_text, parse_mode=constants.ParseMode.MARKDOWN_V2)

# 🚀 Launch Telegram Control Bot
def run_telegram_bot():
    app = ApplicationBuilder().token(Config.TELEGRAM_CONTROL_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("skip", skip))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("nowplaying", nowplaying))
    app.add_handler(CommandHandler("queue", queue))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))

    log.info("🤖 Telegram Control Bot is now running via polling.")
    app.run_polling()

# 🧃 Entry point
if __name__ == "__main__":
    run_telegram_bot()