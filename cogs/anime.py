# ============================================
#   Sansa Bot — Anime Cog
#   Commands: /anime, /anime <title>, /character, /top, /season, /watchtime, /watchlink
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import logging
import random
import asyncio
import difflib
from urllib.parse import quote_plus
from config import (
    CHAT_CHANNEL_ID, COLOR_ANIME, COLOR_ERROR
)
from cogs import mal_client

try:
    import cloudscraper
    from bs4 import BeautifulSoup
except ImportError:
    cloudscraper = None
    BeautifulSoup = None

log = logging.getLogger("SansaBot.Anime")

# ── AniList Queries ────────────────────────
SEARCH_ANIME_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title { romaji english }
    description(asHtml: false)
    episodes
    duration
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

SEARCH_MULTIPLE_QUERY = """
query ($search: String) {
  Page(perPage: 8) {
    media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
      id
      title { romaji english }
      episodes
      duration
      season
      seasonYear
      format
      status
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

class WatchtimeView(discord.ui.View):
    def __init__(self, results, author_id, cog):
        super().__init__(timeout=30.0)
        self.results = results
        self.author_id = author_id
        self.cog = cog
        self.message = None

        options = []
        for i, m in enumerate(results):
            title = m.get("title", {}).get("english") or m.get("title", {}).get("romaji", "Unknown")
            season = m.get("season") or ""
            year = m.get("seasonYear") or ""
            fmt = m.get("format") or ""
            label = title
            if season and year:
                label += f" {season} {year}"
            elif fmt:
                label += f" ({fmt})"
            if len(label) > 100:
                label = label[:97] + "..."
            options.append(discord.SelectOption(label=label, value=str(i)))

        options.append(discord.SelectOption(label="🔥 All Seasons Combined", value="COMBINED"))

        select = discord.ui.Select(
            placeholder="Choose an option...",
            options=options[:25],
            min_values=1,
            max_values=1
        )
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the person who used the command can select.", ephemeral=True)
            return

        value = interaction.data.get("values", [None])[0]
        if value == "COMBINED":
            await self.show_combined(interaction)
        else:
            try:
                idx = int(value)
                media = self.results[idx]
                await self.show_single(interaction, media)
            except (ValueError, IndexError):
                await interaction.response.send_message("❌ Invalid selection.", ephemeral=True)
                return

        self.stop()

    async def show_single(self, interaction, media):
        title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji", "Unknown")
        episodes = media.get("episodes") or 0
        per_ep = self.cog.parse_duration(media.get("duration"))

        if episodes <= 0:
            await interaction.response.send_message("❌ Episode count not available for this title.", ephemeral=True)
            return

        total_min = episodes * per_ep
        total_h = round(total_min / 60, 1)
        total_d = round(total_h / 24, 1)

        embed = discord.Embed(title=f"📺 {title}", color=COLOR_ANIME)
        embed.add_field(name="🎬 Episodes", value=str(episodes), inline=True)
        embed.add_field(name="⏱️ Per Episode", value=f"{per_ep} min", inline=True)
        embed.add_field(name="\u200b", value="─────────────────", inline=False)
        embed.add_field(name="⏱️ Total", value=f"{total_h} hours", inline=False)
        embed.add_field(name="📅 That's", value=f"{total_d} days of your life! 😭", inline=False)

        await interaction.response.edit_message(content=None, embed=embed, view=None)

    async def show_combined(self, interaction):
        lines = []
        grand_total_min = 0

        base_title = self.results[0].get("title", {}).get("english") or self.results[0].get("title", {}).get("romaji", "Series")

        for m in self.results:
            title = m.get("title", {}).get("english") or m.get("title", {}).get("romaji", "Unknown")
            ep = m.get("episodes") or 0
            dur = self.cog.parse_duration(m.get("duration"))
            if ep <= 0:
                continue
            h = round(ep * dur / 60, 1)
            lines.append(f"{title}      →  {ep} ep × {dur} min =  {h} hrs")
            grand_total_min += ep * dur

        if not lines:
            await interaction.response.send_message("❌ No valid data for combined.", ephemeral=True)
            return

        total_h = round(grand_total_min / 60, 1)
        total_d = round(total_h / 24, 1)

        breakdown = "\n".join(lines)
        embed = discord.Embed(title=f"📺 {base_title} — Complete Series", color=COLOR_ANIME)
        embed.add_field(name="Breakdown", value=breakdown, inline=False)
        embed.add_field(name="\u200b", value="─────────────────────────────────", inline=False)
        embed.add_field(name="⏱️ Total", value=f"{total_h} hours", inline=False)
        embed.add_field(name="📅 That's", value=f"{total_d} days of your life! 😭", inline=False)

        await interaction.response.edit_message(content=None, embed=embed, view=None)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(content="⏰ Time's up!\nMenu expired. আবার /watchtime দাও।", view=None)
            except discord.HTTPException:
                pass


class Anime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Anime Cog loaded")

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

    def parse_duration(self, dur):
        if not dur:
            return 24
        if isinstance(dur, (int, float)):
            return int(dur)
        try:
            nums = ''.join(c for c in str(dur) if c.isdigit())
            val = int(nums) if nums else 24
            return val if 1 <= val <= 120 else 24
        except (ValueError, TypeError):
            return 24

    # ── /anime (random) ────────────────────
    @app_commands.command(name="anime", description="🎌 Get details for a random or specific anime (MyAnimeList)")
    @app_commands.describe(title="Anime title (leave empty for random)")
    async def anime(self, interaction: discord.Interaction, title: str = None):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        if title:
            # MAL official → Jikan → AniList
            anime = None
            mal_hits = await mal_client.search_anime(title, limit=1)
            if mal_hits:
                anime = mal_hits[0]
            if not anime:
                data = await self.jikan_request(f"anime?q={title}&limit=1")
                if data and data.get("data"):
                    anime = data["data"][0]
            if not anime:
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
            score_suffix = "/10" if "mal_id" in anime else "/100"
            embed.add_field(name="⭐ Score", value=f"{score}{score_suffix}", inline=True)
            embed.add_field(name="📺 Episodes", value=str(episodes), inline=True)
            embed.add_field(name="📊 Status", value=status, inline=True)
            embed.add_field(name="📅 Year", value=str(year), inline=True)
            embed.add_field(name="🎭 Genres", value=genres, inline=False)
            embed.set_image(url=image_url)
            embed.set_footer(text="Sansa Bot 🌸 • MyAnimeList" if "mal_id" in anime else "Sansa Bot 🌸 • AniList")

        else:
            # Random: MAL → Jikan → AniList
            anime = await mal_client.random_anime()
            if not anime:
                data = await self.jikan_request("random/anime")
                if data and data.get("data"):
                    anime = data["data"]
            if not anime:
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

            score_suffix = "/10" if "mal_id" in anime else "/100"
            embed = discord.Embed(
                title=f"🎲 Random Anime — {title_en}",
                description=f"*{title_jp}*\n\n{desc}",
                color=COLOR_ANIME,
                url=site_url
            )
            embed.add_field(name="⭐ Score", value=f"{score}{score_suffix}", inline=True)
            embed.add_field(name="📺 Episodes", value=str(episodes), inline=True)
            embed.add_field(name="📅 Year", value=str(year), inline=True)
            embed.add_field(name="🎭 Genres", value=genres, inline=False)
            embed.set_image(url=image_url)
            embed.set_footer(text="Sansa Bot 🌸 • MyAnimeList" if "mal_id" in anime else "Sansa Bot 🌸 • AniList")

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

        # MAL → Jikan → AniList
        media_list = await mal_client.top_anime(10)
        if not media_list:
            data = await self.jikan_request("top/anime?limit=10")
            if data and data.get("data"):
                media_list = data["data"]
        if not media_list:
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

            score_suffix = "/10" if "mal_id" in anime else "/100"
            embed.add_field(
                name=f"{i}. {title_en}",
                value=f"⭐ {score}{score_suffix} | 🎭 {genres}",
                inline=False
            )

        if image_url:
            embed.set_thumbnail(url=image_url)
        src = "MyAnimeList" if media_list and "mal_id" in media_list[0] else "AniList"
        embed.set_footer(text=f"Sansa Bot 🌸 • {src}")

        await interaction.followup.send(embed=embed)

    # ── /season ────────────────────────────
    @app_commands.command(name="season", description="📅 Show current season anime list")
    async def season(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
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

        # MAL winter year = year of January (Dec → next year)
        mal_year = year + 1 if (current_season == "WINTER" and month == 12) else year
        media_list = await mal_client.season_anime(mal_year, current_season, 10)
        if not media_list:
            data = await self.jikan_request("seasons/now?limit=10")
            if data and data.get("data"):
                media_list = data["data"]
        if not media_list:
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

            score_suffix = "/10" if "mal_id" in anime else "/100"
            embed.add_field(
                name=f"{i}. {title_en}",
                value=f"⭐ {score}{score_suffix}",
                inline=True
            )

        if "mal_id" in media_list[0]:
            thumb = media_list[0].get("images", {}).get("jpg", {}).get("large_image_url")
        else:
            thumb = media_list[0].get("coverImage", {}).get("large")

        if thumb:
            embed.set_thumbnail(url=thumb)
        src = "MyAnimeList" if media_list and "mal_id" in media_list[0] else "AniList"
        embed.set_footer(text=f"Sansa Bot 🌸 • {src}")

        await interaction.followup.send(embed=embed)

    # ── /watchtime ─────────────────────────
    @app_commands.command(name="watchtime", description="Calculate total watch time for an anime")
    @app_commands.describe(title="Anime title")
    async def watchtime(self, interaction: discord.Interaction, title: str):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        # Use AniList multi search
        data = await self.anilist_request(SEARCH_MULTIPLE_QUERY, {"search": title})
        results = []
        if data and data.get("data", {}).get("Page", {}).get("media"):
            results = data["data"]["Page"]["media"]

        if not results:
            embed = discord.Embed(
                description=f"❌ No anime found with **{title}**!",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        # Case 1: Single result → direct
        if len(results) == 1:
            await self.send_watchtime_single(interaction, results[0])
            return

        # Case 2: Multiple → dropdown
        view = WatchtimeView(results, interaction.user.id, self)
        msg = await interaction.followup.send(
            f"🔍 Multiple results for **{title}**. Select one:",
            view=view
        )
        view.message = msg

    async def send_watchtime_single(self, interaction, media):
        title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji", "Unknown")
        episodes = media.get("episodes") or 0
        per_ep = self.parse_duration(media.get("duration"))

        if episodes <= 0:
            await interaction.followup.send("❌ Episode count not available.")
            return

        total_min = episodes * per_ep
        total_h = round(total_min / 60, 1)
        total_d = round(total_h / 24, 1)

        embed = discord.Embed(title=f"📺 {title}", color=COLOR_ANIME)
        embed.add_field(name="🎬 Episodes", value=str(episodes), inline=True)
        embed.add_field(name="⏱️ Per Episode", value=f"{per_ep} min", inline=True)
        embed.add_field(name="\u200b", value="─────────────────", inline=False)
        embed.add_field(name="⏱️ Total", value=f"{total_h} hours", inline=False)
        embed.add_field(name="📅 That's", value=f"{total_d} days of your life! 😭", inline=False)

        await interaction.followup.send(embed=embed)

    # ── /watchlink ─────────────────────────
    @app_commands.command(name="watchlink", description="🔗 Get direct watch page links (enma + anikoto)")
    @app_commands.describe(title="Anime title")
    async def watchlink(self, interaction: discord.Interaction, title: str):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        if not cloudscraper or not BeautifulSoup:
            # Fallback if no scraper
            sites = {
                "Enma": f"https://www.enma.lol/search?keyword={quote_plus(title)}",
                "Anikoto": f"https://anikototv.to/filter?keyword={quote_plus(title)}",
            }
            embed = discord.Embed(title=f"🔗 Watch Links — {title}", color=COLOR_ANIME)
            for name, url in sites.items():
                embed.add_field(name=name, value=f"[Search]({url})", inline=False)
            await interaction.followup.send(embed=embed)
            return

        sites = [
            {"name": "Enma", "searches": ["https://www.enma.lol/search?keyword={q}"], "domain": "enma.lol"},
            {"name": "Anikoto", "searches": ["https://anikototv.to/filter?keyword={q}"], "domain": "anikototv.to"},
        ]

        embed = discord.Embed(
            title=f"🔗 Watch Links — {title}",
            description="Direct links from working sites (search fallback if needed)",
            color=COLOR_ANIME
        )

        async def find_link(site):
            q = quote_plus(title)
            loop = asyncio.get_running_loop()

            def _scrape_one(url):
                try:
                    scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "mobile": False})
                    resp = scraper.get(url, timeout=8)
                    if resp.status_code != 200:
                        return None
                    soup = BeautifulSoup(resp.text, "lxml")
                    return self._pick_best_match(soup, title, site["domain"])
                except Exception as e:
                    log.warning(f"watchlink {site['name']} {url} err: {e}")
                    return None

            for tmpl in site.get("searches", [site.get("search", "")]):
                search_url = tmpl.format(q=q)
                link = await loop.run_in_executor(None, _scrape_one, search_url)
                if link:
                    return site["name"], link
            # all failed → search link
            return site["name"], site["searches"][0].format(q=q)

        tasks = [find_link(s) for s in sites]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in results:
            if isinstance(item, Exception):
                continue
            name, url = item
            if url.startswith("http"):
                if "/search" in url or "/filter" in url:
                    val = f"[🔍 Search]({url})"
                else:
                    val = f"[▶️ Watch]({url})"
            else:
                val = url
            embed.add_field(name=name, value=val, inline=False)

        await interaction.followup.send(embed=embed)

    def _pick_best_match(self, soup, title: str, domain: str):
        if not soup:
            return None
        title_l = title.lower().strip()
        key_words = [w for w in title_l.split() if len(w) >= 3]
        candidates = []
        good_paths = ("/watch/", "/anime/", "/play/", "/series/", "/stream/", "/detail/", "/title/", "/movie/")

        for a in soup.find_all("a", href=True)[:80]:
            href = a["href"].strip()
            if not href or href == "#" or "javascript" in href.lower():
                continue
            if href.startswith("/"):
                href = f"https://{domain}{href}"
            if domain not in href:
                continue
            # ignore nav/search pages
            bad = ["/search", "/filter", "/home", "/login", "/register", "/genre", "/type", "/tag", "/category"]
            if any(b in href for b in bad):
                continue
            txt = (a.get_text() or "").strip()
            if not txt:
                txt = a.get("title", "") or a.get("aria-label", "") or a.get("data-title", "")
            txt_l = txt.lower()

            # also score slug in url
            slug = href.split("/")[-1].lower().replace("-", " ").replace("_", " ")
            score = difflib.SequenceMatcher(None, title_l, txt_l).ratio()
            score += difflib.SequenceMatcher(None, title_l, slug).ratio() * 0.6

            if any(kw in txt_l or kw in slug for kw in key_words):
                score += 0.3
            # boost if good anime path
            if any(p in href for p in good_paths):
                score += 0.15
            if score >= 0.22:
                candidates.append((score, href, (txt or slug)[:70]))

        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
        return None


async def setup(bot):
    await bot.add_cog(Anime(bot))

