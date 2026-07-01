# ============================================
#   Sansa Bot — Main File
#   Version: 1.0.0
# ============================================

import discord
from discord.ext import commands
import asyncio
import os
import logging
<<<<<<< HEAD
from datetime import datetime, timezone
=======
from datetime import datetime
>>>>>>> 097fcf874c8a1bda660e90da00244b2bb35e86aa
from config import (
    BOT_TOKEN, BOT_PREFIX, BOT_NAME, BOT_VERSION,
    CHAT_CHANNEL_ID,
    ANIME_UPDATES_CHANNEL_ID, SAVE_CHANNEL_ID, COLOR_ERROR
)

# ── Logging Setup ──────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("SansaBot")

# ── Bot Intents ────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True

# ── Bot Setup ──────────────────────────────
bot = commands.Bot(
    command_prefix=BOT_PREFIX,
    intents=intents,
    help_command=None
)

# ── Start Time ─────────────────────────────
<<<<<<< HEAD
bot.start_time = datetime.now(timezone.utc)
=======
bot.start_time = datetime.utcnow()
>>>>>>> 097fcf874c8a1bda660e90da00244b2bb35e86aa

# ── Cogs List ──────────────────────────────
COGS = [
    "cogs.anime",
    "cogs.manga",
    "cogs.memes",
    "cogs.fun",
    "cogs.utils",
    "cogs.auto",
    "cogs.alerts",
]

# ── Channel Check ──────────────────────────
def is_chat_channel(interaction: discord.Interaction) -> bool:
    return interaction.channel_id == CHAT_CHANNEL_ID

# Attach the check to the bot
bot.is_chat_channel  = is_chat_channel

# ── Events ─────────────────────────────────
@bot.event
async def on_ready():
    log.info(f"✅ {BOT_NAME} Bot is online!")
    log.info(f"🤖 Logged in as: {bot.user} (ID: {bot.user.id})")
    log.info(f"📌 Version: {BOT_VERSION}")

    # Slash commands sync
    try:
        synced = await bot.tree.sync()
        log.info(f"🔄 Synced {len(synced)} slash command(s)")
    except Exception as e:
        log.error(f"❌ Sync error: {e}")

    # Bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Anime 🌸"
        )
    )

@bot.event
async def on_interaction(interaction: discord.Interaction):
    # Restrict most commands to #anime-chat channel only
    if interaction.type == discord.InteractionType.application_command:
        channel_id = interaction.channel_id
        command_name = interaction.data.get("name", "")

        chat_only = [
            "anime", "character", "top", "season", "watchtime", "watchlink",
            "manga",
            "memes",
            "quote", "fact", "quiz",
            "help", "commands", "ping", "status", "schedule", "count",
            "epalert", "epremove", "alertlist", "myanime",
            "nextrelease", "animecalendar", "weeklyanime", "trendinganime"
        ]

        if command_name in chat_only:
            if channel_id != CHAT_CHANNEL_ID:
                embed = discord.Embed(
                    description=f"❌ This command only works in <#{CHAT_CHANNEL_ID}>!",
                    color=COLOR_ERROR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

    # Do NOT call process_application_commands — it is removed in modern discord.py
    # Commands are handled automatically by the library.

@bot.event
<<<<<<< HEAD
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    log.error(f"Slash command error: {error}")
    if not interaction.response.is_done():
        await interaction.response.send_message(
            embed=discord.Embed(description=f"❌ Error: {error}", color=COLOR_ERROR),
            ephemeral=True
        )
=======
async def on_command_error(ctx, error):
    log.error(f"Command error: {error}")
>>>>>>> 097fcf874c8a1bda660e90da00244b2bb35e86aa


# ── Save / Unsave Feature (❤️ & ❌) ─────────────────────────────
async def send_temp_message(channel, content: str, delete_after: int = 5):
    """Send a temporary message that deletes itself after X seconds"""
    try:
        msg = await channel.send(content)
        await asyncio.sleep(delete_after)
        await msg.delete()
    except Exception as e:
        log.warning(f"Temp message error: {e}")


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Ignore bot's own reactions
    if payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)

    # ========== SAVE: ❤️ on any bot message ==========
    if emoji == "❤️":
        channel = bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return

        # Only save messages posted by the bot
        if message.author.id != bot.user.id:
            return

        save_channel = bot.get_channel(SAVE_CHANNEL_ID)
        if not save_channel:
            log.warning("SAVE_CHANNEL_ID not configured or channel not found")
            return

        # Build header with context + jump link
        jump_url = message.jump_url
        header = f"❤️ **Saved from** #{channel.name}\n{jump_url}"

        try:
            await save_channel.send(
                content=header,
                embeds=message.embeds,
                files=[await a.to_file() for a in message.attachments] if message.attachments else []
            )
            await send_temp_message(save_channel, "✅ Saved", delete_after=5)
        except Exception as e:
            log.error(f"Failed to save message: {e}")

    # ========== UNSAVE: ❌ only in save channel (owner only) ==========
    elif emoji == "❌":
        if payload.channel_id != SAVE_CHANNEL_ID:
            return

        # Only bot owner can unsave (personal bot)
        if payload.user_id != bot.owner_id:
            return

        channel = bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return

        # Only delete bot's own messages
        if message.author.id == bot.user.id:
            await message.delete()
            await send_temp_message(channel, "🗑️ Removed", delete_after=5)


# ── Load Cogs ──────────────────────────────
async def load_cogs():
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            log.info(f"✅ Loaded: {cog}")
        except Exception as e:
            log.error(f"❌ Failed to load {cog}: {e}")

# ── Main ───────────────────────────────────
async def main():
    async with bot:
        await load_cogs()
        await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
