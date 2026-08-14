# ============================================
#   Sansa Bot — Manga Cog (MyAnimeList only)
#   Commands: /manga, /manga <title>
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import logging
from config import (
    CHAT_CHANNEL_ID, COLOR_MANGA, COLOR_ERROR
)
from cogs import mal_client

log = logging.getLogger("SansaBot.Manga")


class Manga(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Manga Cog loaded (MyAnimeList only)")

    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if CHAT_CHANNEL_ID == 0:
            log.error("[Manga] CHAT_CHANNEL_ID is 0 (not set in .env)!")
            await interaction.response.send_message(
                "❌ Bot misconfigured: CHAT_CHANNEL_ID not set in .env", ephemeral=True
            )
            return False
        if interaction.channel_id != CHAT_CHANNEL_ID:
            embed = discord.Embed(
                description=f"❌ This command only works in <#{CHAT_CHANNEL_ID}>!",
                color=COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    def _embed_from_mal(self, manga: dict, random_mode: bool = False) -> discord.Embed:
        desc = manga.get("synopsis") or manga.get("description") or "No description available."
        if desc and len(desc) > 350:
            desc = desc[:350] + "..."
        genres = manga.get("genres") or []
        if genres and isinstance(genres[0], dict):
            genres_s = ", ".join([g.get("name", "") for g in genres][:4]) or "Unknown"
        else:
            genres_s = ", ".join(str(g) for g in genres[:4]) or "Unknown"
        title_obj = manga.get("title")
        if isinstance(title_obj, dict):
            title_en = title_obj.get("english") or title_obj.get("romaji", "Unknown")
            title_jp = title_obj.get("romaji", "")
        else:
            title_en = manga.get("title_english") or title_obj or "Unknown"
            title_jp = title_obj or ""
        score = manga.get("score", manga.get("averageScore", "N/A"))
        prefix = "🎲 Random Manga — " if random_mode else "📚 "
        embed = discord.Embed(
            title=f"{prefix}{title_en}"[:256],
            description=f"*{title_jp}*\n\n{desc}",
            color=COLOR_MANGA,
            url=manga.get("siteUrl") or manga.get("site_url") or None,
        )
        embed.add_field(name="⭐ Score", value=f"{score}/10", inline=True)
        embed.add_field(name="📖 Chapters", value=str(manga.get("chapters", "N/A")), inline=True)
        embed.add_field(name="📦 Volumes", value=str(manga.get("volumes", "N/A")), inline=True)
        if not random_mode:
            embed.add_field(name="📊 Status", value=str(manga.get("status", "Unknown")), inline=True)
            embed.add_field(name="✍️ Author", value=str(manga.get("author", "Unknown")), inline=True)
        year = manga.get("year")
        if year in (None, "N/A") and isinstance(manga.get("startDate"), dict):
            year = manga["startDate"].get("year", "N/A")
        embed.add_field(name="📅 Year", value=str(year if year is not None else "N/A"), inline=True)
        embed.add_field(name="🎭 Genres", value=genres_s, inline=False)
        img = None
        if manga.get("coverImage"):
            img = manga["coverImage"].get("extraLarge") or manga["coverImage"].get("large")
        if not img and manga.get("images"):
            img = manga["images"].get("jpg", {}).get("large_image_url")
        if img:
            embed.set_image(url=img)
        embed.set_footer(text="Sansa Bot 🌸 • MyAnimeList")
        return embed

    @app_commands.command(name="manga", description="📚 Get details for a random or specific manga (MyAnimeList)")
    @app_commands.describe(title="Manga title (leave empty for random)")
    async def manga(self, interaction: discord.Interaction, title: str = None):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        if title:
            hits = await mal_client.search_manga(title, limit=1)
            if not hits:
                embed = discord.Embed(
                    description=f"❌ No manga found with the name **{title}**!",
                    color=COLOR_ERROR,
                )
                await interaction.followup.send(embed=embed)
                return
            await interaction.followup.send(embed=self._embed_from_mal(hits[0], random_mode=False))
            log.info(f"[Manga] /manga MAL: {title}")
            return

        manga = await mal_client.random_manga()
        if not manga:
            embed = discord.Embed(
                description="❌ Failed to fetch manga from MyAnimeList. Try again.",
                color=COLOR_ERROR,
            )
            await interaction.followup.send(embed=embed)
            return
        await interaction.followup.send(embed=self._embed_from_mal(manga, random_mode=True))
        log.info("[Manga] /manga random MAL ok")

    async def fetch_random_manga(self):
        """Used by auto.py for hourly manga posts."""
        return await mal_client.random_manga()


async def setup(bot):
    await bot.add_cog(Manga(bot))
    log.info("✅ Manga Cog setup complete (MyAnimeList only)")
