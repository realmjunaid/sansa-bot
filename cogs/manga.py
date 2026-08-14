# ============================================
#   Sansa Bot — Manga Cog
#   Commands: /manga, /manga <title>
#   Primary: MyAnimeList API → AniList fallback
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import logging
import random
from config import (
    CHAT_CHANNEL_ID, COLOR_MANGA, COLOR_ERROR
)
from cogs import mal_client

log = logging.getLogger("SansaBot.Manga")

# ── AniList Queries (fallback) ─────────────
SEARCH_MANGA_QUERY = """
query ($search: String) {
  Media(search: $search, type: MANGA) {
    id
    title { romaji english }
    description(asHtml: false)
    chapters
    volumes
    averageScore
    genres
    status
    startDate { year month day }
    coverImage { extraLarge }
    siteUrl
    staff {
      edges {
        role
        node { name { full } }
      }
    }
  }
}
"""

RANDOM_MANGA_QUERY = """
query ($page: Int) {
  Page(page: $page, perPage: 1) {
    media(type: MANGA, sort: POPULARITY_DESC, status: FINISHED) {
      id
      title { romaji english }
      description(asHtml: false)
      chapters
      volumes
      averageScore
      genres
      startDate { year }
      coverImage { extraLarge }
      siteUrl
    }
  }
}
"""

class Manga(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Manga Cog loaded (MAL primary, commands in #anime-chat)")

    # ── Channel Check ──────────────────────
    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if CHAT_CHANNEL_ID == 0:
            log.error("[Manga] CHAT_CHANNEL_ID is 0 (not set in .env)!")
            await interaction.response.send_message("❌ Bot misconfigured: CHAT_CHANNEL_ID not set in .env", ephemeral=True)
            return False
        if interaction.channel_id != CHAT_CHANNEL_ID:
            ch = interaction.guild.get_channel(CHAT_CHANNEL_ID) if interaction.guild else None
            ch_name = ch.name if ch else "anime-chat"
            log.warning(f"[Manga] Blocked /manga from #{getattr(interaction.channel, 'name', 'unknown')} (need #{ch_name} id={CHAT_CHANNEL_ID})")
            embed = discord.Embed(
                description=f"❌ This command only works in <#{CHAT_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    # ── AniList Request ────────────────────
    async def anilist_request(self, query: str, variables: dict = {}):
        timeout = aiohttp.ClientTimeout(total=12)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    "https://graphql.anilist.co",
                    json={"query": query, "variables": variables},
                    headers={"Content-Type": "application/json", "User-Agent": "SansaBot/1.0"}
                ) as resp:
                    log.info(f"[Manga] AniList POST status={resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        return data
                    else:
                        text = await resp.text()
                        log.warning(f"[Manga] AniList bad status {resp.status}: {text[:200]}")
        except Exception as e:
            log.error(f"[Manga] AniList request error: {e}")
        return None

    def _embed_from_mal(self, manga: dict, random_mode: bool = False) -> discord.Embed:
        desc = manga.get("synopsis") or manga.get("description") or "No description available."
        if desc and len(desc) > 350:
            desc = desc[:350] + "..."
        genres = manga.get("genres") or []
        if genres and isinstance(genres[0], dict):
            genres_s = ", ".join([g.get("name", "") for g in genres][:4]) or "Unknown"
        else:
            genres_s = ", ".join(genres[:4]) or "Unknown"
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
            title=f"{prefix}{title_en}",
            description=f"*{title_jp}*\n\n{desc}",
            color=COLOR_MANGA,
            url=manga.get("siteUrl") or manga.get("site_url") or ""
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

    # ── /manga ─────────────────────────────
    @app_commands.command(name="manga", description="📚 Get details for a random or specific manga (MyAnimeList)")
    @app_commands.describe(title="Manga title (leave empty for random)")
    async def manga(self, interaction: discord.Interaction, title: str = None):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        if title:
            # MAL first
            mal_hits = await mal_client.search_manga(title, limit=1)
            if mal_hits:
                embed = self._embed_from_mal(mal_hits[0], random_mode=False)
                await interaction.followup.send(embed=embed)
                log.info(f"[Manga] /manga MAL hit: {title}")
                return

            data = await self.anilist_request(SEARCH_MANGA_QUERY, {"search": title})
            if not data or not data.get("data", {}).get("Media"):
                embed = discord.Embed(
                    description=f"❌ No manga found with the name **{title}**!",
                    color=COLOR_ERROR
                )
                await interaction.followup.send(embed=embed)
                return

            manga = data["data"]["Media"]
            log.info(f"[Manga] /manga AniList hit: {title}")

            desc = manga.get("description", "No description available.")
            if desc and len(desc) > 350:
                desc = desc[:350] + "..."

            genres = ", ".join(manga.get("genres", [])[:4]) or "Unknown"
            title_en = manga["title"].get("english") or manga["title"].get("romaji", "Unknown")
            title_jp = manga["title"].get("romaji", "")

            author = "Unknown"
            staff_edges = manga.get("staff", {}).get("edges", [])
            for edge in staff_edges:
                if "Story" in edge.get("role", "") or "Art" in edge.get("role", ""):
                    author = edge["node"]["name"]["full"]
                    break

            status_map = {
                "FINISHED": "✅ Finished",
                "RELEASING": "📡 Ongoing",
                "NOT_YET_RELEASED": "🔜 Upcoming",
                "CANCELLED": "❌ Cancelled",
                "HIATUS": "⏸️ Hiatus"
            }
            status = status_map.get(manga.get("status", ""), "Unknown")

            sd = manga.get("startDate", {})
            air_date = f"{sd.get('day', '?')}/{sd.get('month', '?')}/{sd.get('year', '?')}"

            embed = discord.Embed(
                title=f"📚 {title_en}",
                description=f"*{title_jp}*\n\n{desc}",
                color=COLOR_MANGA,
                url=manga.get("siteUrl", "")
            )
            embed.add_field(name="⭐ Score", value=f"{manga.get('averageScore', 'N/A')}/100", inline=True)
            embed.add_field(name="📖 Chapters", value=str(manga.get("chapters", "N/A")), inline=True)
            embed.add_field(name="📦 Volumes", value=str(manga.get("volumes", "N/A")), inline=True)
            embed.add_field(name="📊 Status", value=status, inline=True)
            embed.add_field(name="✍️ Author", value=author, inline=True)
            embed.add_field(name="📅 Started", value=air_date, inline=True)
            embed.add_field(name="🎭 Genres", value=genres, inline=False)
            embed.set_image(url=manga["coverImage"]["extraLarge"])
            embed.set_footer(text="Sansa Bot 🌸 • AniList")

        else:
            manga = await mal_client.random_manga()
            if manga:
                embed = self._embed_from_mal(manga, random_mode=True)
                await interaction.followup.send(embed=embed)
                log.info("[Manga] /manga random MAL ok")
                return

            manga = None
            for _ in range(5):
                page = random.randint(1, 50)
                data = await self.anilist_request(RANDOM_MANGA_QUERY, {"page": page})
                if data and data.get("data") and data["data"].get("Page") and data["data"]["Page"].get("media"):
                    manga = data["data"]["Page"]["media"][0]
                    break
            if not manga:
                embed = discord.Embed(
                    description="❌ Failed to fetch manga. Set MAL_CLIENT_ID in .env or try again.",
                    color=COLOR_ERROR
                )
                await interaction.followup.send(embed=embed)
                log.warning("[Manga] Random manga failed")
                return

            desc = manga.get("description", "No description.")
            if desc and len(desc) > 350:
                desc = desc[:350] + "..."

            genres = ", ".join(manga.get("genres", [])[:4]) or "Unknown"
            title_en = manga["title"].get("english") or manga["title"].get("romaji", "Unknown")
            title_jp = manga["title"].get("romaji", "")

            embed = discord.Embed(
                title=f"🎲 Random Manga — {title_en}",
                description=f"*{title_jp}*\n\n{desc}",
                color=COLOR_MANGA,
                url=manga.get("siteUrl", "")
            )
            embed.add_field(name="⭐ Score", value=f"{manga.get('averageScore', 'N/A')}/100", inline=True)
            embed.add_field(name="📖 Chapters", value=str(manga.get("chapters", "N/A")), inline=True)
            embed.add_field(name="📦 Volumes", value=str(manga.get("volumes", "N/A")), inline=True)
            embed.add_field(name="📅 Year", value=str(manga.get("startDate", {}).get("year", "N/A")), inline=True)
            embed.add_field(name="🎭 Genres", value=genres, inline=False)
            embed.set_image(url=manga["coverImage"]["extraLarge"])
            embed.set_footer(text="Sansa Bot 🌸 • AniList")

        await interaction.followup.send(embed=embed)
        log.info("[Manga] /manga command completed successfully")

    async def fetch_random_manga(self):
        """Used by auto.py for hourly manga posts. Returns media dict or None."""
        manga = await mal_client.random_manga()
        if manga:
            return manga
        for _ in range(5):
            page = random.randint(1, 50)
            data = await self.anilist_request(RANDOM_MANGA_QUERY, {"page": page})
            if data and data.get("data") and data["data"].get("Page") and data["data"]["Page"].get("media"):
                return data["data"]["Page"]["media"][0]
        return None


async def setup(bot):
    await bot.add_cog(Manga(bot))
    log.info("✅ Manga Cog setup complete (MAL + AniList fallback)")
