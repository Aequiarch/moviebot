import os
import json
import uuid
import asyncio
from datetime import datetime

import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
from discord import ButtonStyle, Embed, Interaction, TextChannel

from core.config import Config
from core.utils.logger import get_logger
from core.utils.filelock import read_locked_json, write_locked_json
from core.queue import get_now_playing

log = get_logger("discordbot")

CONTROL_FILE = "control.json"
CONTROL_BUTTONS = {
    "pause": {"emoji": "⏸️", "label": "Pause", "style": ButtonStyle.secondary},
    "resume": {"emoji": "▶️", "label": "Resume", "style": ButtonStyle.success},
    "skip": {"emoji": "⏭️", "label": "Skip", "style": ButtonStyle.primary},
    "stop": {"emoji": "⏹️", "label": "Stop", "style": ButtonStyle.danger},
    "reload": {"emoji": "🔁", "label": "Reload", "style": ButtonStyle.secondary},
}

intents = discord.Intents.default()
intents.guilds = True
intents.messages = False
intents.message_content = False

bot = commands.Bot(command_prefix="!", intents=intents)


class ControlView(View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=None)
        self.user = user

        for cmd, meta in CONTROL_BUTTONS.items():
            self.add_item(
                Button(
                    label=meta["label"],
                    emoji=meta["emoji"],
                    style=meta["style"],
                    custom_id=f"moviebot:{cmd}"
                )
            )

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Optional: Role validation
        return True

    async def on_error(self, interaction: Interaction, error: Exception, item):
        log.error(f"❌ Button interaction error: {error}")
        await interaction.response.send_message("⚠️ Something went wrong.", ephemeral=True)


def build_control_embed() -> Embed:
    """Builds the control panel embed from the current movie metadata."""
    data = get_now_playing()
    if not data:
        return Embed(
            title="🎬 No Movie Currently Playing",
            description="Use the upload bot or wait for the next queued video.",
            color=0x2f3136
        )

    embed = Embed(
        title=f"🎥 Now Playing: {data['title']}",
        description=(
            f"📁 Source: `{data.get('type', 'Unknown')}`\n"
            f"🕒 Duration: {data.get('duration', '?')}s\n"
            f"👤 Requested by: `{data.get('added_by', 'Anonymous')}`"
        ),
        color=0x2b2d31
    )
    embed.set_footer(text=f"Started at: {datetime.now().strftime('%H:%M:%S')}")
    return embed


async def post_control_panel():
    """Clears the last few messages and posts the control embed."""
    try:
        channel: TextChannel = bot.get_channel(int(Config.DISCORD_CHANNEL_ID))
        if not channel:
            log.error("❌ Invalid Discord channel ID. Channel not found.")
            return

        await channel.purge(limit=5)
        embed = build_control_embed()
        view = ControlView(user=bot.user)
        await channel.send(embed=embed, view=view)
        log.info("✅ Posted control panel to Discord.")

    except Exception as e:
        log.error(f"⚠️ Could not post control panel: {e}")


@bot.event
async def on_ready():
    log.info(f"✅ Logged in as: {bot.user} (ID: {bot.user.id})")
    await post_control_panel()


@bot.event
async def on_interaction(interaction: Interaction):
    if not interaction.data or "custom_id" not in interaction.data:
        return

    custom_id = interaction.data.get("custom_id")
    if not custom_id or not custom_id.startswith("moviebot:"):
        return

    command = custom_id.split(":")[1]
    if command not in CONTROL_BUTTONS:
        await interaction.response.send_message("⚠️ Invalid command.", ephemeral=True)
        return

    try:
        data = read_locked_json(CONTROL_FILE)
        if not isinstance(data, dict):
            data = {}

        data[command] = {
            "id": str(uuid.uuid4()),
            "user": interaction.user.name
        }

        write_locked_json(CONTROL_FILE, data)
        log.info(f"📥 {interaction.user.name} issued `{command}`")
        await interaction.response.send_message(f"✅ `{command}` command sent.", ephemeral=True)

        # Optional: Immediately refresh embed panel after interaction
        await post_control_panel()

    except Exception as e:
        log.error(f"❌ Failed to process interaction: {e}")
        await interaction.response.send_message("⚠️ Command failed to send.", ephemeral=True)


def run_discord_bot():
    log.info("🎮 Starting Discord bot...")
    try:
        bot.run(Config.DISCORD_BOT_TOKEN)
    except Exception as e:
        log.critical(f"🔥 Discord bot crashed: {e}")


if __name__ == "__main__":
    run_discord_bot()
