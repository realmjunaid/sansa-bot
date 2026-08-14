# ============================================
#   Sansa Bot — Auto Post Cog
#   Anime/Manga/Memes: Every hour
# ============================================

import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import logging
import random
import re
from datetime import datetime, timezone
from config import (
    ANIME_CHANNEL_ID,
    MANGA_CHANNEL_ID, MEMES_CHANNEL_ID,
    COLOR_ANIME, COLOR_MANGA, COLOR_MEMES
)
from cogs import mal_client

log = logging.getLogger("SansaBot.Auto")

# ── AniList Query ──────────────────────────
ANIME_QUERY = """
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

class Auto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.anime_count_today = 0
        self.manga_count_today = 0
        self.memes_count_today = 0
        self.last_reset = datetime.now(timezone.utc).date()

        self.auto_anime.start()
        self.auto_manga.start()
        self.auto_memes.start()
        log.info("✅ Auto Cog loaded")

    def cog_unload(self):
        self.auto_anime.cancel()
        self.auto_manga.cancel()
        self.auto_memes.cancel()

    # ── Daily Count Reset ──────────────────
    def check_reset(self):
        today = datetime.now(timezone.utc).date()
        if today != self.last_reset:
            self.anime_count_today = 0
            self.manga_count_today = 0
            self.memes_count_today = 0
            self.last_reset = today

    # ── Anime Fetch (MAL → Jikan → AniList) ───────────────────────
    async def fetch_random_anime(self):
        # Primary: official MyAnimeList API
        mal = await mal_client.random_anime()
        if mal:
            genres = [g.get("name") if isinstance(g, dict) else g for g in mal.get("genres", [])]
            img = (mal.get("images") or {}).get("jpg", {}).get("large_image_url") or ""
            return {
                "title": {
                    "romaji": mal.get("title", ""),
                    "english": mal.get("title_english") or mal.get("title", "")
                },
                "description": mal.get("synopsis", ""),
                "episodes": mal.get("episodes"),
                "averageScore": mal.get("score"),
                "genres": genres,
                "startDate": {"year": mal.get("year")},
                "coverImage": {"extraLarge": img},
                "siteUrl": f"https://myanimelist.net/anime/{mal.get('mal_id')}",
                "_score_out_of": 10,
            }

        # Fallback: Jikan
        try:
            async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}) as session:
                async with session.get("https://api.jikan.moe/v4/random/anime", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        anime = data.get("data")
                        if anime:
                            return {
                                "title": {
                                    "romaji": anime.get("title", ""),
                                    "english": anime.get("title_english") or anime.get("title", "")
                                },
                                "description": anime.get("synopsis", ""),
                                "episodes": anime.get("episodes"),
                                "averageScore": anime.get("score"),
                                "genres": [g.get("name") for g in anime.get("genres", [])],
                                "startDate": {"year": anime.get("year")},
                                "coverImage": {"extraLarge": anime.get("images", {}).get("jpg", {}).get("large_image_url") or anime.get("images", {}).get("jpg", {}).get("image_url")},
                                "siteUrl": f"https://myanimelist.net/anime/{anime.get('mal_id')}",
                                "_score_out_of": 10,
                            }
        except Exception as e:
            log.warning(f"Jikan failed — falling back to AniList: {e}")

        # Fallback: AniList
        try:
            page = random.randint(1, 50)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://graphql.anilist.co",
                    json={"query": ANIME_QUERY, "variables": {"page": page}},
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        media_list = data["data"]["Page"]["media"]
                        if media_list:
                            m = media_list[0]
                            m["_score_out_of"] = 100
                            return m
        except Exception as e:
            log.error(f"AniList fallback also failed: {e}")
        return None

    # ── Auto Anime (প্রতি ঘণ্টায় - 24 টা) ───
    @tasks.loop(hours=1)
    async def auto_anime(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        channel = self.bot.get_channel(ANIME_CHANNEL_ID)
        if not channel:
            log.error("❌ Anime channel not found!")
            return

        anime = await self.fetch_random_anime()
        if not anime:
            return

        self.anime_count_today += 1

        desc = anime.get("description", "No description available.")
        if desc and len(desc) > 300:
            desc = desc[:300] + "..."

        genres = ", ".join(anime.get("genres", [])[:4]) or "Unknown"
        title_en = anime["title"].get("english") or anime["title"].get("romaji", "Unknown")
        title_jp = anime["title"].get("romaji", "")

        embed = discord.Embed(
            title=f"🎌 {title_en}",
            description=f"*{title_jp}*\n\n{desc}",
            color=COLOR_ANIME,
            url=anime.get("siteUrl", ""),
            timestamp=datetime.now(timezone.utc)
        )
        score_max = anime.get("_score_out_of", 100)
        embed.add_field(name="⭐ Score", value=f"{anime.get('averageScore', 'N/A')}/{score_max}", inline=True)
        embed.add_field(name="📺 Episodes", value=str(anime.get("episodes", "N/A")), inline=True)
        embed.add_field(name="📅 Year", value=str(anime.get("startDate", {}).get("year", "N/A")), inline=True)
        embed.add_field(name="🎭 Genres", value=genres, inline=False)
        cover = anime.get("coverImage") or {}
        if cover.get("extraLarge"):
            embed.set_image(url=cover["extraLarge"])
        embed.set_footer(text="Sansa Bot • MyAnimeList" if score_max == 10 else "Sansa Bot • AniList")

        await channel.send(embed=embed)
        log.info(f"✅ Auto anime posted ({self.anime_count_today}/24)")

    @auto_anime.before_loop
    async def before_auto_anime(self):
        await self.bot.wait_until_ready()

    # ── Auto Manga (প্রতি ঘণ্টায়) ─────────
    @tasks.loop(hours=1)
    async def auto_manga(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        channel = self.bot.get_channel(MANGA_CHANNEL_ID)
        if not channel:
            return

        manga_cog = self.bot.get_cog("Manga")
        if not manga_cog:
            return

        manga = await manga_cog.fetch_random_manga()
        if not manga:
            return

        self.manga_count_today += 1

        desc = manga.get("description", "No description available.")
        if desc and len(desc) > 300:
            desc = desc[:300] + "..."

        genres = ", ".join(manga.get("genres", [])[:4]) or "Unknown"
        title_en = manga["title"].get("english") or manga["title"].get("romaji", "Unknown")
        title_jp = manga["title"].get("romaji", "")

        embed = discord.Embed(
            title=f"📚 {title_en}",
            description=f"*{title_jp}*\n\n{desc}",
            color=COLOR_MANGA,
            url=manga.get("siteUrl", ""),
            timestamp=datetime.now(timezone.utc)
        )
        score_max = 10 if manga.get("_source") == "mal" or manga.get("mal_id") else 100
        score_val = manga.get("averageScore", manga.get("score", "N/A"))
        embed.add_field(name="⭐ Score", value=f"{score_val}/{score_max}", inline=True)
        embed.add_field(name="📖 Chapters", value=str(manga.get("chapters", "N/A")), inline=True)
        embed.add_field(name="📦 Volumes", value=str(manga.get("volumes", "N/A")), inline=True)
        year = manga.get("startDate", {}).get("year") if isinstance(manga.get("startDate"), dict) else manga.get("year", "N/A")
        embed.add_field(name="📅 Year", value=str(year if year is not None else "N/A"), inline=True)
        embed.add_field(name="🎭 Genres", value=genres, inline=False)
        cover = manga.get("coverImage") or {}
        img = cover.get("extraLarge") or cover.get("large")
        if img:
            embed.set_image(url=img)
        embed.set_footer(text="Sansa Bot • MyAnimeList" if score_max == 10 else "Sansa Bot • AniList")

        await channel.send(embed=embed)
        log.info(f"✅ Auto manga posted ({self.manga_count_today}/24)")

    @auto_manga.before_loop
    async def before_auto_manga(self):
        await self.bot.wait_until_ready()

    # ── Auto Memes (প্রতি ঘণ্টায়) ─────────
    @tasks.loop(hours=1)
    async def auto_memes(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        channel = self.bot.get_channel(MEMES_CHANNEL_ID)
        if not channel:
            return

        memes_cog = self.bot.get_cog("Memes")
        if not memes_cog:
            return

        meme = await memes_cog.fetch_meme("hot")
        if not meme:
            return

        self.memes_count_today += 1

        embed = memes_cog.build_embed(meme, "🔥 Auto Meme")
        embed.set_footer(text=f"Sansa Bot • Auto Memes • {self.memes_count_today}/24")
        await channel.send(embed=embed)
        log.info(f"✅ Auto memes posted ({self.memes_count_today}/24)")

    @auto_memes.before_loop
    async def before_auto_memes(self):
        await self.bot.wait_until_ready()

    @property
    def anime_today(self):
        return self.anime_count_today

    @property
    def manga_today(self):
        return self.manga_count_today

    @property
    def memes_today(self):
        return self.memes_count_today


async def setup(bot):
    await bot.add_cog(Auto(bot))
