# ============================================
#   Sansa Bot — Utils Cog
#   Commands: /help, /ping, /status, /schedule, /count
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import logging
import platform
from datetime import datetime, timezone
from config import (
    CHAT_CHANNEL_ID, WAIFU_CHANNEL_ID, ANIME_CHANNEL_ID,
    COLOR_UTIL, COLOR_ERROR, BOT_NAME, BOT_VERSION, BOT_AUTHOR
)

log = logging.getLogger("SansaBot.Utils")

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Utils Cog loaded")

    # ── Channel Check ──────────────────────
    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != CHAT_CHANNEL_ID:
            embed = discord.Embed(
                description=f"❌ This command only works in <#{CHAT_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    # ── /help ──────────────────────────────
    @app_commands.command(name="help", description="📋 Show list of all commands")
    async def help(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        embed = discord.Embed(
            title="📋 Sansa Bot — Command List",
            description="All commands only work in **#anime-chat**!",
            color=COLOR_UTIL
        )

        embed.add_field(
            name="🌸 Waifu Commands",
            value=(
                "`/image` — Random waifu image\n"
                "`/waifu` — Random ecchi waifu images (15)\n"
                "`/tag <name>` — Get image by tag"
            ),
            inline=False
        )

        embed.add_field(
            name="🎌 Anime Commands",
            value=(
                "`/anime` — Random anime details\n"
                "`/anime <title>` — Specific anime details\n"
                "`/character <name>` — Character details + image\n"
                "`/top` — Top 10 Anime (MyAnimeList)\n"
                "`/season` — Current season anime list"
            ),
            inline=False
        )

        embed.add_field(
            name="📚 Manga Commands",
            value=(
                "`/manga` — Random manga details\n"
                "`/manga <title>` — Specific manga details"
            ),
            inline=False
        )

        embed.add_field(
            name="😂 Memes Commands",
            value=(
                "`/memes` — Random anime meme\n"
                "`/memes hot` — 🔥 Hot memes\n"
                "`/memes new` — 🆕 Latest memes\n"
                "`/memes funny` — 😂 Funny memes"
            ),
            inline=False
        )

        embed.add_field(
            name="🎉 Fun Commands",
            value=(
                "`/quote` — Random anime quote\n"
                "`/fact` — Random anime fact\n"
                "`/quiz` — Anime trivia quiz"
            ),
            inline=False
        )

        embed.add_field(
            name="⚙️ Utility Commands",
            value=(
                "`/help` — This list\n"
                "`/ping` — Bot latency\n"
                "`/status` — Bot status\n"
                "`/schedule` — Next auto post countdown\n"
                "`/count` — Today's total post count"
            ),
            inline=False
        )

        embed.add_field(
            name="🤖 Auto Features",
            value=(
                "**#waifu-zone** — Waifu image every hour\n"
                "**#anime-zone** — Random anime every hour\n"
                "**#hanime** — NSFW hentai every hour (12 images per post) + /hanime commands\n"
                "**#hdad** — hentaidad.com hentai every hour (12 images per post)\n"
                "**#sakuh** — Sakuhentai images every hour (15 images of the same character)"
            ),
            inline=False
        )

        embed.add_field(
            name="🔞 NSFW Commands",
            value=(
                "`/hanime` — Random hentai (12 images)\n"
                "`/hanime <character>` — Search hentai by character/anime name\n"
                "`/hdad` — Random hentai (12 images)\n"
                "`/hdad <name>` — Search hentai by character/title\n"
                "`/saku` — 15 images of the same character from Sakuhentai"
            ),
            inline=False
        )

        embed.set_footer(text=f"Sansa Bot v{BOT_VERSION} 🌸 • Made by {BOT_AUTHOR}")
        await interaction.response.send_message(embed=embed)

    # ── /ping ──────────────────────────────
    @app_commands.command(name="ping", description="🏓 Show bot latency")
    async def ping(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        latency = round(self.bot.latency * 1000)

        if latency < 100:
            status = "🟢 Excellent"
            color = 0x2ECC71
        elif latency < 200:
            status = "🟡 Good"
            color = 0xF1C40F
        else:
            status = "🔴 Poor"
            color = 0xFF0000

        embed = discord.Embed(
            title="🏓 Pong!",
            color=color
        )
        embed.add_field(name="📡 Latency", value=f"`{latency}ms`", inline=True)
        embed.add_field(name="📊 Status", value=status, inline=True)
        embed.set_footer(text="Sansa Bot 🌸")
        await interaction.response.send_message(embed=embed)

    # ── /status ────────────────────────────
    @app_commands.command(name="status", description="📊 Show bot status")
    async def status(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        now = datetime.now(timezone.utc)
        start_time = self.bot.start_time.replace(tzinfo=timezone.utc)
        uptime = now - start_time

        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days = uptime.days

        uptime_str = f"{days}d {hours % 24}h {minutes}m {seconds}s"

        # Auto cog থেকে count নাও
        auto_cog = self.bot.cogs.get("Auto")
        waifu_count = auto_cog.waifu_today if auto_cog else 0
        anime_count = auto_cog.anime_today if auto_cog else 0
        hzone_count = auto_cog.hzone_today if auto_cog else 0

        embed = discord.Embed(
            title=f"📊 {BOT_NAME} Bot Status",
            color=COLOR_UTIL,
            timestamp=now
        )
        embed.add_field(name="🤖 Bot Name", value=BOT_NAME, inline=True)
        embed.add_field(name="📌 Version", value=f"v{BOT_VERSION}", inline=True)
        embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
        embed.add_field(name="📡 Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="🌸 Waifu Today", value=f"{waifu_count}/24", inline=True)
        embed.add_field(name="🎌 Anime Today", value=f"{anime_count}/24", inline=True)
        embed.add_field(name="🔞 Hzone Today", value=f"{hzone_count}/24", inline=True)
        embed.add_field(name="🐍 Python", value=platform.python_version(), inline=True)
        embed.add_field(name="📚 discord.py", value=discord.__version__, inline=True)
        embed.set_footer(text="Sansa Bot 🌸")
        await interaction.response.send_message(embed=embed)

    # ── /schedule ──────────────────────────
    @app_commands.command(name="schedule", description="⏰ Show countdown to next auto post")
    async def schedule(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        now = datetime.now(timezone.utc)
        current_hour = now.hour
        current_minute = now.minute

        # Next waifu post
        next_waifu_minutes = 60 - current_minute
        next_waifu_str = f"in {next_waifu_minutes} minutes"

        embed = discord.Embed(
            title="⏰ Auto Post Schedule",
            color=COLOR_UTIL,
            timestamp=now
        )
        embed.add_field(
            name="🌸 Next Waifu Post",
            value=f"**#{interaction.guild.get_channel(WAIFU_CHANNEL_ID).name if interaction.guild.get_channel(WAIFU_CHANNEL_ID) else 'waifu-zone'}**\n⏱️ {next_waifu_str}",
            inline=False
        )
        embed.add_field(
            name="🎌 Anime Posts",
            value="**Every hour** in #anime-zone",
            inline=False
        )
        embed.set_footer(text="Sansa Bot 🌸 • UTC Time")
        await interaction.response.send_message(embed=embed)

    # ── /count ─────────────────────────────
    @app_commands.command(name="count", description="📈 Show today's total post count")
    async def count(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        auto_cog = self.bot.cogs.get("Auto")
        waifu_count = auto_cog.waifu_today if auto_cog else 0
        anime_count = auto_cog.anime_today if auto_cog else 0
        hanime_count = auto_cog.hanime_today if auto_cog else 0
        hzone_count = auto_cog.hzone_today if auto_cog else 0

        embed = discord.Embed(
            title="📈 Today's Auto Post Count",
            color=COLOR_UTIL,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(
            name="🌸 Waifu Posts",
            value=f"**{waifu_count}/24**\n{'▓' * waifu_count}{'░' * (24 - waifu_count)}",
            inline=False
        )
        embed.add_field(
            name="🎌 Anime Posts",
            value=f"**{anime_count}/24**\n{'▓' * anime_count}{'░' * (24 - anime_count)}",
            inline=False
        )
        embed.add_field(
            name="🔞 Hanime Posts (NSFW)",
            value=f"**{hanime_count}/24** (12 images each)\n{'▓' * hanime_count}{'░' * (24 - hanime_count)}",
            inline=False
        )
        embed.add_field(
            name="🔞 Hzone Posts (NSFW - hentaidad)",
            value=f"**{hzone_count}/24** (12 images each)\n{'▓' * hzone_count}{'░' * (24 - hzone_count)}",
            inline=False
        )
        embed.set_footer(text="Sansa Bot 🌸 • Resets at midnight UTC")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Utils(bot))
