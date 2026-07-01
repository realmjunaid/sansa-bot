# ============================================
#   Sansa Bot — Utils Cog
#   Commands: /help, /commands, /ping, /status, /schedule, /count
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import logging
import platform
from datetime import datetime, timezone
from config import (
    CHAT_CHANNEL_ID,
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
            name="🎌 Anime Commands",
            value=(
                "`/anime` — Random anime details\n"
                "`/anime <title>` — Specific anime details\n"
                "`/character <name>` — Character details + image\n"
                "`/top` — Top 10 Anime (MyAnimeList)\n"
                "`/season` — Current season anime list\n"
                "`/watchtime <title>` — Total watch time calculator\n"
                "`/watchlink <title>` — Find streaming page links (enma, anikoto)"
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
            name="📡 Episode Alerts",
            value=(
                "`/epalert <anime>` — Track for episode reminders\n"
                "`/epremove <anime>` — Stop tracking\n"
                "`/alertlist` — Your tracked list\n"
                "`/myanime` — Detailed dashboard\n"
                "`/nextrelease` — Upcoming countdowns\n"
                "`/animecalendar` — Weekly schedule\n"
                "`/weeklyanime` — Last 7 days releases\n"
                "`/trendinganime` — Current top 10"
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
                "`/commands` — Live list of all slash commands (from tree)\n"
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
                "**#anime-zone** — Random anime every hour\n"
                "**#manga-zone** — Random manga every hour\n"
                "**#memes-zone** — Anime meme every hour"
            ),
            inline=False
        )

        embed.set_footer(text=f"Sansa Bot v{BOT_VERSION} 🌸 • Made by {BOT_AUTHOR}")
        await interaction.response.send_message(embed=embed)

    # ── Category map for grouping live commands (matches /help sections) ──
    CATEGORY_MAP = {
        "Anime": "🎌 Anime Commands",
        "Alerts": "📡 Episode Alerts",
        "Manga": "📚 Manga Commands",
        "Memes": "😂 Memes Commands",
        "Fun": "🎉 Fun Commands",
        "Utils": "⚙️ Utility Commands",
    }

    def _format_command(self, cmd: app_commands.AppCommand) -> str:
        """Format a single AppCommand with params and choices."""
        name = cmd.name
        desc = cmd.description or "No description"
        parts = []
        for opt in cmd.options or []:
            p = f"<{opt.name}>" if opt.required else f"[{opt.name}]"
            if opt.choices:
                ch = "|".join(c.value for c in opt.choices)
                p += f" ({ch})"
            parts.append(p)
        param_str = " " + " ".join(parts) if parts else ""
        return f"`/{name}{param_str}` — {desc}"

    # ── /commands (live tree introspection) ──────────────────────────────
    @app_commands.command(name="commands", description="📜 Show all slash commands (live from tree)")
    async def commands(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        tree_cmds = self.bot.tree.get_commands()
        groups: dict[str, list[str]] = {}

        for cmd in tree_cmds:
            if not isinstance(cmd, app_commands.AppCommand):
                continue
            cog_name = cmd.binding.__class__.__name__ if cmd.binding else "Global"
            cat = self.CATEGORY_MAP.get(cog_name, f"Other ({cog_name})")
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(self._format_command(cmd))

        embed = discord.Embed(
            title="📜 Sansa Bot — Live Command List",
            description="Generated from bot.tree at runtime. No manual list.",
            color=COLOR_UTIL
        )

        # Preserve logical order matching /help
        ordered_cats = [
            "🎌 Anime Commands",
            "📡 Episode Alerts",
            "📚 Manga Commands",
            "😂 Memes Commands",
            "🎉 Fun Commands",
            "⚙️ Utility Commands",
        ]

        for cat in ordered_cats:
            if cat in groups and groups[cat]:
                embed.add_field(name=cat, value="\n".join(groups[cat]), inline=False)

        embed.set_footer(
            text="Channel restrictions still apply. Use /help for friendly docs + auto features."
        )
        await interaction.followup.send(embed=embed)

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
        anime_count = auto_cog.anime_today if auto_cog else 0
        manga_count = auto_cog.manga_today if auto_cog else 0
        memes_count = auto_cog.memes_today if auto_cog else 0

        embed = discord.Embed(
            title=f"📊 {BOT_NAME} Bot Status",
            color=COLOR_UTIL,
            timestamp=now
        )
        embed.add_field(name="🤖 Bot Name", value=BOT_NAME, inline=True)
        embed.add_field(name="📌 Version", value=f"v{BOT_VERSION}", inline=True)
        embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
        embed.add_field(name="📡 Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="🎌 Anime Today", value=f"{anime_count}/24", inline=True)
        embed.add_field(name="📚 Manga Today", value=f"{manga_count}/24", inline=True)
        embed.add_field(name="😂 Memes Today", value=f"{memes_count}/24", inline=True)
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

        embed = discord.Embed(
            title="⏰ Auto Post Schedule",
            color=COLOR_UTIL,
            timestamp=now
        )
        embed.add_field(
            name="🎌 Anime Posts",
            value="**Every hour** in #anime-zone",
            inline=False
        )
        embed.add_field(
            name="📚 Manga + 😂 Memes",
            value="**Every hour** (if #manga-zone / #memes-zone set)",
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
        anime_count = auto_cog.anime_today if auto_cog else 0
        manga_count = auto_cog.manga_today if auto_cog else 0
        memes_count = auto_cog.memes_today if auto_cog else 0

        embed = discord.Embed(
            title="📈 Today's Auto Post Count",
            color=COLOR_UTIL,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(
            name="🎌 Anime Posts",
            value=f"**{anime_count}/24**\n{'▓' * anime_count}{'░' * (24 - anime_count)}",
            inline=False
        )
        embed.add_field(
            name="📚 Manga Posts",
            value=f"**{manga_count}/24**\n{'▓' * manga_count}{'░' * (24 - manga_count)}",
            inline=False
        )
        embed.add_field(
            name="😂 Memes Posts",
            value=f"**{memes_count}/24**\n{'▓' * memes_count}{'░' * (24 - memes_count)}",
            inline=False
        )
        embed.set_footer(text="Sansa Bot 🌸 • Resets at midnight UTC")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Utils(bot))
