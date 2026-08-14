# ============================================
#   Sansa Bot — Auto Post Cog
#   Anime/Manga: MyAnimeList only | Memes: Reddit
# ============================================

import discord
from discord.ext import commands, tasks
import logging
from datetime import datetime, timezone
from config import (
    ANIME_CHANNEL_ID,
    MANGA_CHANNEL_ID, MEMES_CHANNEL_ID,
    COLOR_ANIME, COLOR_MANGA,
)
from cogs import mal_client

log = logging.getLogger("SansaBot.Auto")


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
        log.info("✅ Auto Cog loaded (MAL-only anime/manga)")

    def cog_unload(self):
        self.auto_anime.cancel()
        self.auto_manga.cancel()
        self.auto_memes.cancel()

    def check_reset(self):
        today = datetime.now(timezone.utc).date()
        if today != self.last_reset:
            self.anime_count_today = 0
            self.manga_count_today = 0
            self.memes_count_today = 0
            self.last_reset = today

    # ── Anime (MyAnimeList only) ───────────
    async def fetch_random_anime(self):
        mal = await mal_client.random_anime()
        if not mal:
            return None
        genres = [g.get("name") if isinstance(g, dict) else g for g in mal.get("genres", [])]
        img = (mal.get("images") or {}).get("jpg", {}).get("large_image_url") or ""
        return {
            "title": {
                "romaji": mal.get("title", ""),
                "english": mal.get("title_english") or mal.get("title", ""),
            },
            "description": mal.get("synopsis", ""),
            "episodes": mal.get("episodes"),
            "averageScore": mal.get("score"),
            "genres": genres,
            "startDate": {"year": mal.get("year")},
            "coverImage": {"extraLarge": img},
            "siteUrl": mal.get("site_url")
            or f"https://myanimelist.net/anime/{mal.get('mal_id')}",
        }

    @tasks.loop(hours=1)
    async def auto_anime(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        if not ANIME_CHANNEL_ID:
            log.error("❌ ANIME_CHANNEL_ID is 0")
            return
        channel = self.bot.get_channel(ANIME_CHANNEL_ID)
        if not channel:
            log.error(f"❌ Anime channel not found (id={ANIME_CHANNEL_ID})")
            return

        anime = await self.fetch_random_anime()
        if not anime:
            log.warning("⚠️ Auto anime: MAL fetch failed")
            return

        self.anime_count_today += 1

        desc = anime.get("description") or "No description available."
        if len(desc) > 300:
            desc = desc[:300] + "..."

        genres = ", ".join(anime.get("genres", [])[:4]) or "Unknown"
        title_en = anime["title"].get("english") or anime["title"].get("romaji", "Unknown")
        title_jp = anime["title"].get("romaji", "")

        embed = discord.Embed(
            title=f"🎌 {title_en}",
            description=f"*{title_jp}*\n\n{desc}",
            color=COLOR_ANIME,
            url=anime.get("siteUrl") or None,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="⭐ Score", value=f"{anime.get('averageScore', 'N/A')}/10", inline=True)
        embed.add_field(name="📺 Episodes", value=str(anime.get("episodes", "N/A")), inline=True)
        embed.add_field(
            name="📅 Year",
            value=str(anime.get("startDate", {}).get("year", "N/A")),
            inline=True,
        )
        embed.add_field(name="🎭 Genres", value=genres, inline=False)
        cover = anime.get("coverImage") or {}
        if cover.get("extraLarge"):
            embed.set_image(url=cover["extraLarge"])
        embed.set_footer(text="Sansa Bot • MyAnimeList")

        try:
            await channel.send(embed=embed)
            log.info(f"✅ Auto anime posted ({self.anime_count_today}/24)")
        except Exception as e:
            log.error(f"❌ Auto anime send failed: {e}")

    @auto_anime.before_loop
    async def before_auto_anime(self):
        await self.bot.wait_until_ready()

    # ── Manga (MyAnimeList only) ───────────
    @tasks.loop(hours=1)
    async def auto_manga(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        if not MANGA_CHANNEL_ID:
            log.error("❌ MANGA_CHANNEL_ID is 0")
            return
        channel = self.bot.get_channel(MANGA_CHANNEL_ID)
        if not channel:
            log.error(f"❌ Manga channel not found (id={MANGA_CHANNEL_ID})")
            return

        manga_cog = self.bot.get_cog("Manga")
        manga = await (manga_cog.fetch_random_manga() if manga_cog else mal_client.random_manga())
        if not manga:
            log.warning("⚠️ Auto manga: MAL fetch failed")
            return

        self.manga_count_today += 1

        desc = manga.get("description") or manga.get("synopsis") or "No description available."
        if len(desc) > 300:
            desc = desc[:300] + "..."

        genres_raw = manga.get("genres") or []
        if genres_raw and isinstance(genres_raw[0], dict):
            genres = ", ".join([g.get("name", "") for g in genres_raw][:4]) or "Unknown"
        else:
            genres = ", ".join(str(g) for g in genres_raw[:4]) or "Unknown"

        title_obj = manga.get("title")
        if isinstance(title_obj, dict):
            title_en = title_obj.get("english") or title_obj.get("romaji", "Unknown")
            title_jp = title_obj.get("romaji", "")
        else:
            title_en = manga.get("title_english") or title_obj or "Unknown"
            title_jp = title_obj or ""

        embed = discord.Embed(
            title=f"📚 {title_en}",
            description=f"*{title_jp}*\n\n{desc}",
            color=COLOR_MANGA,
            url=manga.get("siteUrl") or manga.get("site_url") or None,
            timestamp=datetime.now(timezone.utc),
        )
        score_val = manga.get("averageScore", manga.get("score", "N/A"))
        embed.add_field(name="⭐ Score", value=f"{score_val}/10", inline=True)
        embed.add_field(name="📖 Chapters", value=str(manga.get("chapters", "N/A")), inline=True)
        embed.add_field(name="📦 Volumes", value=str(manga.get("volumes", "N/A")), inline=True)
        year = (
            manga.get("startDate", {}).get("year")
            if isinstance(manga.get("startDate"), dict)
            else manga.get("year", "N/A")
        )
        embed.add_field(name="📅 Year", value=str(year if year is not None else "N/A"), inline=True)
        embed.add_field(name="🎭 Genres", value=genres, inline=False)
        cover = manga.get("coverImage") or {}
        img = cover.get("extraLarge") or cover.get("large")
        if img:
            embed.set_image(url=img)
        embed.set_footer(text="Sansa Bot • MyAnimeList")

        try:
            await channel.send(embed=embed)
            log.info(f"✅ Auto manga posted ({self.manga_count_today}/24)")
        except Exception as e:
            log.error(f"❌ Auto manga send failed: {e}")

    @auto_manga.before_loop
    async def before_auto_manga(self):
        await self.bot.wait_until_ready()

    # ── Memes ──────────────────────────────
    @tasks.loop(hours=1)
    async def auto_memes(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        if not MEMES_CHANNEL_ID:
            log.error("❌ MEMES_CHANNEL_ID is 0 — set it in .env")
            return

        channel = self.bot.get_channel(MEMES_CHANNEL_ID)
        if not channel:
            log.error(f"❌ Memes channel not found (id={MEMES_CHANNEL_ID})")
            return

        memes_cog = self.bot.get_cog("Memes")
        if not memes_cog:
            log.error("❌ Memes cog not loaded — cannot auto-post memes")
            return

        meme = await memes_cog.fetch_meme("hot")
        if not meme:
            log.warning("⚠️ Auto memes: fetch failed this hour")
            return

        self.memes_count_today += 1

        try:
            embed = memes_cog.build_embed(meme, "🔥 Auto Meme")
            embed.set_footer(text=f"Sansa Bot • Auto Memes • {self.memes_count_today}/24")
            await channel.send(embed=embed)
            log.info(f"✅ Auto memes posted ({self.memes_count_today}/24)")
        except Exception as e:
            log.error(f"❌ Auto memes send failed: {e}")

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
