# ============================================
#   Sansa Bot — Anime Cog
#   Commands: /anime, /anime <title>, /character, /top, /season
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import logging
import random
from config import (
    ANIME_CHANNEL_ID, COLOR_ANIME, COLOR_ERROR
)

log = logging.getLogger("SansaBot.Anime")

# ── AniList Queries ────────────────────────
SEARCH_ANIME_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title { romaji english }
    description(asHtml: false)
    episodes
    averageScore
    genres
    status
    startDate { year month day }
    endDate { year }
    coverImage { extraLarge }
    siteUrl
    studios { nodes { name isAnimationStudio } }
  }
}
"""

RANDOM_ANIME_QUERY = """
query ($page: Int) {
  Page(page: $page, perPage: 1) {
    media(type: ANIME, sort: POPULARITY_DESC, status: FINISHED) {
      id
      title { romaji english }
      description(asHtml: false)
      episodes
      averageScore
      genres
      startDate { year }
      coverImage { extraLarge }
      siteUrl
    }
  }
}
"""

TOP_ANIME_QUERY = """
query {
  Page(page: 1, perPage: 10) {
    media(type: ANIME, sort: SCORE_DESC) {
      id
      title { romaji english }
      averageScore
      episodes
      genres
      coverImage { large }
      siteUrl
    }
  }
}
"""

SEASON_ANIME_QUERY = """
query ($season: MediaSeason, $year: Int) {
  Page(page: 1, perPage: 10) {
    media(type: ANIME, season: $season, seasonYear: $year, sort: POPULARITY_DESC) {
      id
      title { romaji english }
      averageScore
      episodes
      genres
      coverImage { large }
      siteUrl
    }
  }
}
"""

CHARACTER_QUERY = """
query ($search: String) {
  Character(search: $search) {
    id
    name { full native }
    description(asHtml: false)
    image { large }
    gender
    age
    siteUrl
    media(perPage: 1) {
      nodes {
        title { romaji english }
        coverImage { large }
      }
    }
  }
}
"""

class Anime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Anime Cog loaded")

    # ── Channel Check ──────────────────────
    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != ANIME_CHANNEL_ID:
            embed = discord.Embed(
                description=f"❌ This command only works in <#{ANIME_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    # ── AniList Request ────────────────────
    async def anilist_request(self, query: str, variables: dict = {}):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://graphql.anilist.co",
                    json={"query": query, "variables": variables},
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            log.error(f"AniList request error: {e}")
        return None

    # ── Jikan Request (MyAnimeList) ────────────────────
    async def jikan_request(self, endpoint: str):
        """Fetch from Jikan (MyAnimeList) with basic error handling"""
        url = f"https://api.jikan.moe/v4/{endpoint}"
        try:
            async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}) as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            log.warning(f"Jikan request failed for {endpoint}: {e}")
        return None

    # ── /anime (random) ────────────────────
    @app_commands.command(name="anime", description="🎌 Get details for a random or specific anime (MyAnimeList)")
    @app_commands.describe(title="Anime title (leave empty for random)")
    async def anime(self, interaction: discord.Interaction, title: str = None):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        if title:
            # Specific anime search - Try Jikan first
            data = await self.jikan_request(f"anime?q={title}&limit=1")
            anime = None

            if data and data.get("data"):
                anime = data["data"][0]
            else:
                # Fallback to AniList
                data = await self.anilist_request(SEARCH_ANIME_QUERY, {"search": title})
                if data and data.get("data", {}).get("Media"):
                    anime = data["data"]["Media"]

            if not anime:
                embed = discord.Embed(
                    description=f"❌ No anime found with the name **{title}**!",
                    color=COLOR_ERROR
                )
                await interaction.followup.send(embed=embed)
                return

            # Handle both Jikan and AniList structures
            if "mal_id" in anime:  # Jikan structure
                desc = anime.get("synopsis", "No description available.")
                title_en = anime.get("title_english") or anime.get("title", "Unknown")
                title_jp = anime.get("title", "")
                score = anime.get("score", "N/A")
                episodes = anime.get("episodes", "N/A")
                year = anime.get("year", "N/A")
                genres = ", ".join([g.get("name", "") for g in anime.get("genres", [])][:4]) or "Unknown"
                image_url = anime.get("images", {}).get("jpg", {}).get("large_image_url") or anime.get("images", {}).get("jpg", {}).get("image_url")
                site_url = f"https://myanimelist.net/anime/{anime.get('mal_id')}"
                status = anime.get("status", "Unknown")
            else:  # AniList structure
                desc = anime.get("description", "No description available.")
                title_en = anime["title"].get("english") or anime["title"].get("romaji", "Unknown")
                title_jp = anime["title"].get("romaji", "")
                score = anime.get("averageScore", "N/A")
                episodes = anime.get("episodes", "N/A")
                year = anime.get("startDate", {}).get("year", "N/A")
                genres = ", ".join(anime.get("genres", [])[:4]) or "Unknown"
                image_url = anime["coverImage"]["extraLarge"]
                site_url = anime.get("siteUrl", "")
                status_map = {
                    "FINISHED": "✅ Finished",
                    "RELEASING": "📡 Ongoing",
                    "NOT_YET_RELEASED": "🔜 Upcoming",
                    "CANCELLED": "❌ Cancelled"
                }
                status = status_map.get(anime.get("status", ""), "Unknown")

            if desc and len(desc) > 350:
                desc = desc[:350] + "..."

            embed = discord.Embed(
                title=f"🎌 {title_en}",
                description=f"*{title_jp}*\n\n{desc}",
                color=COLOR_ANIME,
                url=site_url
            )
            embed.add_field(name="⭐ Score", value=f"{score}/100", inline=True)
            embed.add_field(name="📺 Episodes", value=str(episodes), inline=True)
            embed.add_field(name="📊 Status", value=status, inline=True)
            embed.add_field(name="📅 Year", value=str(year), inline=True)
            embed.add_field(name="🎭 Genres", value=genres, inline=False)
            embed.set_image(url=image_url)

        else:
            # Random anime - Jikan first
            data = await self.jikan_request("random/anime")
            anime = None

            if data and data.get("data"):
                anime = data["data"]
            else:
                # Fallback
                page = random.randint(1, 50)
                data = await self.anilist_request(RANDOM_ANIME_QUERY, {"page": page})
                if data:
                    anime = data["data"]["Page"]["media"][0]

            if not anime:
                embed = discord.Embed(
                    description="❌ Failed to fetch anime. Please try again.",
                    color=COLOR_ERROR
                )
                await interaction.followup.send(embed=embed)
                return

            # Handle both structures
            if "mal_id" in anime:  # Jikan
                desc = anime.get("synopsis", "No description.")
                title_en = anime.get("title_english") or anime.get("title", "Unknown")
                title_jp = anime.get("title", "")
                score = anime.get("score", "N/A")
                episodes = anime.get("episodes", "N/A")
                year = anime.get("year", "N/A")
                genres = ", ".join([g.get("name", "") for g in anime.get("genres", [])][:4]) or "Unknown"
                image_url = anime.get("images", {}).get("jpg", {}).get("large_image_url") or anime.get("images", {}).get("jpg", {}).get("image_url")
                site_url = f"https://myanimelist.net/anime/{anime.get('mal_id')}"
            else:  # AniList
                desc = anime.get("description", "No description.")
                title_en = anime["title"].get("english") or anime["title"].get("romaji", "Unknown")
                title_jp = anime["title"].get("romaji", "")
                score = anime.get("averageScore", "N/A")
                episodes = anime.get("episodes", "N/A")
                year = anime.get("startDate", {}).get("year", "N/A")
                genres = ", ".join(anime.get("genres", [])[:4]) or "Unknown"
                image_url = anime["coverImage"]["extraLarge"]
                site_url = anime.get("siteUrl", "")

            if desc and len(desc) > 350:
                desc = desc[:350] + "..."

            embed = discord.Embed(
                title=f"🎲 Random Anime — {title_en}",
                description=f"*{title_jp}*\n\n{desc}",
                color=COLOR_ANIME,
                url=site_url
            )
            embed.add_field(name="⭐ Score", value=f"{score}/100", inline=True)
            embed.add_field(name="📺 Episodes", value=str(episodes), inline=True)
            embed.add_field(name="📅 Year", value=str(year), inline=True)
            embed.add_field(name="🎭 Genres", value=genres, inline=False)
            embed.set_image(url=image_url)

        await interaction.followup.send(embed=embed)

    # ── /character <name> ──────────────────
    @app_commands.command(name="character", description="👤 Get details for an anime character")
    @app_commands.describe(name="Character name")
    async def character(self, interaction: discord.Interaction, name: str):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        # Try Jikan first
        data = await self.jikan_request(f"characters?q={name}&limit=1")
        char = None

        if data and data.get("data"):
            char = data["data"][0]
        else:
            # Fallback
            data = await self.anilist_request(CHARACTER_QUERY, {"search": name})
            if data and data.get("data", {}).get("Character"):
                char = data["data"]["Character"]

        if not char:
            embed = discord.Embed(
                description=f"❌ No character found with the name **{name}**!",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        # Handle both structures
        if "mal_id" in char:  # Jikan
            full_name = char.get("name", "Unknown")
            native_name = ""
            desc = char.get("about", "No description available.")
            gender = "Unknown"
            age = "Unknown"
            anime_from = "Unknown"
            # Try to get first anime
            anime_list = char.get("anime", [])
            if anime_list:
                anime_from = anime_list[0].get("anime", {}).get("title", "Unknown")
            image_url = char.get("images", {}).get("jpg", {}).get("image_url")
            site_url = f"https://myanimelist.net/character/{char.get('mal_id')}"
        else:  # AniList
            full_name = char["name"].get("full", "Unknown")
            native_name = char["name"].get("native", "")
            desc = char.get("description", "No description available.")
            gender = char.get("gender", "Unknown")
            age = char.get("age", "Unknown")
            media_nodes = char.get("media", {}).get("nodes", [])
            anime_from = "Unknown"
            if media_nodes:
                an = media_nodes[0]
                anime_from = an["title"].get("english") or an["title"].get("romaji", "Unknown")
            image_url = char["image"]["large"]
            site_url = char.get("siteUrl", "")

        if desc and len(desc) > 350:
            desc = desc[:350] + "..."

        embed = discord.Embed(
            title=f"👤 {full_name}",
            description=f"*{native_name}*\n\n{desc}",
            color=COLOR_ANIME,
            url=site_url
        )
        embed.add_field(name="⚧ Gender", value=gender, inline=True)
        embed.add_field(name="🎂 Age", value=age, inline=True)
        embed.add_field(name="📺 From", value=anime_from, inline=True)
        embed.set_image(url=image_url)

        await interaction.followup.send(embed=embed)

    # ── /top ───────────────────────────────
    @app_commands.command(name="top", description="🏆 Show Top 10 Anime (MyAnimeList)")
    async def top(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        # Try Jikan first
        data = await self.jikan_request("top/anime?limit=10")
        media_list = []

        if data and data.get("data"):
            media_list = data["data"]
        else:
            # Fallback to AniList
            data = await self.anilist_request(TOP_ANIME_QUERY)
            if data:
                media_list = data["data"]["Page"]["media"]

        if not media_list:
            embed = discord.Embed(
                description="❌ Failed to fetch top anime!",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="🏆 Top 10 Anime",
            color=COLOR_ANIME
        )

        for i, anime in enumerate(media_list[:10], 1):
            if "mal_id" in anime:  # Jikan
                title_en = anime.get("title_english") or anime.get("title", "Unknown")
                score = anime.get("score", "N/A")
                genres = ", ".join([g.get("name", "") for g in anime.get("genres", [])][:2])
                image_url = anime.get("images", {}).get("jpg", {}).get("large_image_url")
            else:  # AniList
                title_en = anime["title"].get("english") or anime["title"].get("romaji", "Unknown")
                score = anime.get("averageScore", "N/A")
                genres = ", ".join(anime.get("genres", [])[:2])
                image_url = anime.get("coverImage", {}).get("large")

            embed.add_field(
                name=f"{i}. {title_en}",
                value=f"⭐ {score}/100 | 🎭 {genres}",
                inline=False
            )

        if image_url:
            embed.set_thumbnail(url=image_url)

        await interaction.followup.send(embed=embed)

    # ── /season ────────────────────────────
    @app_commands.command(name="season", description="📅 Show current season anime list")
    async def season(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        from datetime import datetime
        now = datetime.utcnow()
        month = now.month
        year = now.year

        season_map = {
            (12, 1, 2): "WINTER",
            (3, 4, 5): "SPRING",
            (6, 7, 8): "SUMMER",
            (9, 10, 11): "FALL"
        }

        current_season = "WINTER"
        for months, season in season_map.items():
            if month in months:
                current_season = season
                break

        # Try Jikan first (current season)
        data = await self.jikan_request("seasons/now?limit=10")
        media_list = []

        if data and data.get("data"):
            media_list = data["data"]
        else:
            # Fallback to AniList
            data = await self.anilist_request(
                SEASON_ANIME_QUERY,
                {"season": current_season, "year": year}
            )
            if data:
                media_list = data["data"]["Page"]["media"]

        if not media_list:
            embed = discord.Embed(
                description="❌ Failed to fetch season anime!",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"📅 Current Season Anime",
            color=COLOR_ANIME
        )

        for i, anime in enumerate(media_list[:10], 1):
            if "mal_id" in anime:  # Jikan
                title_en = anime.get("title_english") or anime.get("title", "Unknown")
                score = anime.get("score", "N/A")
            else:  # AniList
                title_en = anime["title"].get("english") or anime["title"].get("romaji", "Unknown")
                score = anime.get("averageScore", "N/A")

            embed.add_field(
                name=f"{i}. {title_en}",
                value=f"⭐ {score}/100",
                inline=True
            )

        if "mal_id" in media_list[0]:
            thumb = media_list[0].get("images", {}).get("jpg", {}).get("large_image_url")
        else:
            thumb = media_list[0].get("coverImage", {}).get("large")

        if thumb:
            embed.set_thumbnail(url=thumb)

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Anime(bot))
