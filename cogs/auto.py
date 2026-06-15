# ============================================
#   Sansa Bot — Auto Post Cog
#   Waifu: প্রতি ঘণ্টায়
#   Anime: Every hour (24/day) via Jikan + AniList fallback
# ============================================

import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import logging
import random
import re
from datetime import datetime
from config import (
    WAIFU_CHANNEL_ID, ANIME_CHANNEL_ID, HANIME_CHANNEL_ID,
    HDAD_CHANNEL_ID, SAKUH_CHANNEL_ID, LUCI_CHANNEL_ID,
    WAIFU_TAGS, COLOR_WAIFU, COLOR_ANIME
)

log = logging.getLogger("SansaBot.Auto")


def get_nice_title(url: str) -> str:
    if not url:
        return "Sakuhentai"
    try:
        slug = url.rstrip("/").split("/")[-1]
        slug = re.sub(r'(-hentai-gallery.*|-gallery.*)$', '', slug, flags=re.IGNORECASE)
        title = slug.replace('-', ' ').replace('_', ' ').title()
        return title[:70] if title else "Sakuhentai"
    except Exception:
        return "Sakuhentai"


def get_anime_name(url: str) -> str:
    if not url:
        return "Unknown"
    try:
        slug = str(url).lower()
        anime_map = {
            "demon-slayer": "Demon Slayer",
            "kimetsu-no-yaiba": "Demon Slayer",
            "my-hero-academia": "My Hero Academia",
            "boku-no-hero": "My Hero Academia",
            "naruto": "Naruto",
            "one-piece": "One Piece",
            "bleach": "Bleach",
            "jujutsu-kaisen": "Jujutsu Kaisen",
            "attack-on-titan": "Attack on Titan",
            "shingeki-no-kyojin": "Attack on Titan",
            "chainsaw-man": "Chainsaw Man",
            "spy-x-family": "Spy x Family",
            "solo-leveling": "Solo Leveling",
            "fairy-tail": "Fairy Tail",
            "black-clover": "Black Clover",
            "dragon-ball": "Dragon Ball",
            "dandadan": "Dandadan",
            "oshi-no-ko": "Oshi no Ko",
            "blue-archive": "Blue Archive",
            "konosuba": "KonoSuba",
            "classroom-of-the-elite": "Classroom of the Elite",
            "danmachi": "DanMachi",
            "oregairu": "Oregairu",
            "to-love-ru": "To Love Ru",
            "yu-gi-oh": "Yu-Gi-Oh!",
            "highschool-of-the-dead": "Highschool of the Dead",
        }
        for key, name in anime_map.items():
            if key in slug:
                return name
        parts = url.rstrip("/").split("/")[-1].split("-")
        if len(parts) >= 3:
            return " ".join(parts[-3:]).title()
        return "Sakuhentai"
    except Exception:
        return "Sakuhentai"

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
        self.waifu_count_today = 0
        self.anime_count_today = 0
        self.hanime_count_today = 0
        self.hzone_count_today = 0
        self.last_reset = datetime.utcnow().date()

        self.auto_waifu.start()
        self.auto_anime.start()
        self.auto_hanime.start()
        self.auto_hdad.start()
        self.auto_sakuh.start()
        self.auto_luci.start()
        log.info("✅ Auto Cog loaded")

    def cog_unload(self):
        self.auto_waifu.cancel()
        self.auto_anime.cancel()
        self.auto_hanime.cancel()
        self.auto_hdad.cancel()
        self.auto_sakuh.cancel()
        self.auto_luci.cancel()

    # ── Daily Count Reset ──────────────────
    def check_reset(self):
        today = datetime.utcnow().date()
        if today != self.last_reset:
            self.waifu_count_today = 0
            self.anime_count_today = 0
            self.hanime_count_today = 0
            self.hzone_count_today = 0
            self.last_reset = today

    # ── Waifu Fetch (Safebooru for metadata + fallback) ───────────────────────
    async def fetch_waifu(self):
        timeout = aiohttp.ClientTimeout(total=8)

        # Try Safebooru first
        try:
            tags = "1girl solo rating:s"
            url = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=6&tags={tags}"
            async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}, timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        posts = data if isinstance(data, list) else data.get("post", []) if isinstance(data, dict) else []
                        if posts:
                            post = random.choice(posts)
                            image_url = post.get("file_url") or post.get("sample_url")
                            if image_url:
                                raw_tags = post.get("tags", "").split()
                                character = "Unknown"
                                series = "Unknown"

                                good_tags = [t.replace("_", " ").title() for t in raw_tags
                                             if len(t) > 5 and "_" in t and not any(x in t for x in ["1girl","solo","hair","eyes","rating"])]
                                if good_tags:
                                    character = good_tags[0]

                                possible_series = [t for t in raw_tags if any(x in t for x in ["naruto","one_piece","bleach","demon","jujutsu","genshin","honkai","fate","pokemon","dragon","titan","hero"])]
                                if possible_series:
                                    series = possible_series[0].replace("_", " ").title()

                                log.info(f"✅ Auto waifu from Safebooru ({character})")
                                return {
                                    "url": image_url,
                                    "character": character,
                                    "series": series
                                }
        except Exception as e:
            log.warning(f"Auto waifu Safebooru failed: {e}")

        # Fallback nekos.best
        try:
            url = "https://nekos.best/api/v2/neko"
            async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}, timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        if results:
                            log.info("✅ Auto waifu from nekos.best (fallback)")
                            return {
                                "url": results[0].get("url"),
                                "character": "Random Waifu",
                                "series": "Various"
                            }
        except Exception as e:
            log.warning(f"Auto waifu nekos.best fallback failed: {e}")

        # Last: Purrbot
        try:
            url = "https://api.purrbot.site/v2/img/sfw/neko/img"
            async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}, timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("link"):
                            log.info("✅ Auto waifu from Purrbot (last fallback)")
                            return {
                                "url": data["link"],
                                "character": "Random Waifu",
                                "series": "Various"
                            }
        except Exception as e:
            log.warning(f"Auto waifu Purrbot failed: {e}")

        log.error("❌ Auto waifu: All sources failed")
        return None

    # ── Anime Fetch (Jikan + AniList Fallback) ───────────────────────
    async def fetch_random_anime(self):
        # Primary: Jikan (MyAnimeList)
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
                                "siteUrl": f"https://myanimelist.net/anime/{anime.get('mal_id')}"
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
                            return media_list[0]
        except Exception as e:
            log.error(f"AniList fallback also failed: {e}")
        return None

    # ── Auto Waifu (প্রতি ঘণ্টায়) ─────────
    @tasks.loop(hours=1)
    async def auto_waifu(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        channel = self.bot.get_channel(WAIFU_CHANNEL_ID)
        if not channel:
            log.error("❌ Waifu channel not found!")
            return

        waifu_cog = self.bot.get_cog("Waifu")
        if not waifu_cog:
            return

        images = await waifu_cog.fetch_waifu_images(count=15)
        if not images:
            return

        self.waifu_count_today += 1

        for img in images:
            embed = discord.Embed(color=COLOR_WAIFU)
            embed.set_image(url=img["url"])
            await channel.send(embed=embed)

        log.info(f"✅ Auto waifu posted 15 images ({self.waifu_count_today}/24)")

    @auto_waifu.before_loop
    async def before_auto_waifu(self):
        await self.bot.wait_until_ready()

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
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="⭐ Score", value=f"{anime.get('averageScore', 'N/A')}/100", inline=True)
        embed.add_field(name="📺 Episodes", value=str(anime.get("episodes", "N/A")), inline=True)
        embed.add_field(name="📅 Year", value=str(anime.get("startDate", {}).get("year", "N/A")), inline=True)
        embed.add_field(name="🎭 Genres", value=genres, inline=False)
        embed.set_image(url=anime["coverImage"]["extraLarge"])

        await channel.send(embed=embed)
        log.info(f"✅ Auto anime posted ({self.anime_count_today}/24)")

    @auto_anime.before_loop
    async def before_auto_anime(self):
        await self.bot.wait_until_ready()

    # ── Auto Hanime (NSFW) - Every Hour ───────
    @tasks.loop(hours=1)
    async def auto_hanime(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        channel = self.bot.get_channel(HANIME_CHANNEL_ID)
        if not channel:
            return

        hanime_cog = self.bot.get_cog("Hanime")
        if not hanime_cog:
            return

        post = await hanime_cog.get_random_hentai_post()
        if not post or not post.get("images"):
            return

        self.hanime_count_today += 1

        embed = discord.Embed(
            title=f"🔞 {post['character']}",
            color=0xFF69B4,
            timestamp=datetime.utcnow()
        )

        if post.get("info"):
            embed.add_field(name="📖 About", value=post["info"]["about"][:250], inline=False)

        embed.add_field(name="📊 Today", value=f"{self.hanime_count_today}/24", inline=True)
        embed.set_footer(text="Sansa Bot • NSFW • Nekobot")
        await channel.send(embed=embed)

        for i, img in enumerate(post["images"][:12], 1):
            img_embed = discord.Embed(color=0xFF69B4)
            img_embed.set_image(url=img["url"])
            img_embed.set_footer(text=f"{post['character']} • {i}/12")
            await channel.send(embed=img_embed)

        log.info(f"✅ Auto hanime posted ({self.hanime_count_today}/24)")

    @auto_hanime.before_loop
    async def before_auto_hanime(self):
        await self.bot.wait_until_ready()

    # ── Auto Hdad (hentaidad.com) - Every Hour ───────
    @tasks.loop(hours=1)
    async def auto_hdad(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        channel = self.bot.get_channel(HDAD_CHANNEL_ID)
        if not channel:
            return

        hdad_cog = self.bot.get_cog("Hentaidad")
        if not hdad_cog:
            return

        post = await hdad_cog.get_random_hzone_post()
        if not post or not post.get("images"):
            return

        self.hzone_count_today += 1
        images_to_post = post["images"][:15]
        total = len(images_to_post)

        header = discord.Embed(
            title=f"🔞 {post['character']}",
            color=0xE91E63,
            timestamp=datetime.utcnow()
        )
        header.add_field(
            name="🔗 Source",
            value=post.get("source_url", "https://hentaidad.com"),
            inline=False
        )
        header.add_field(name="📸 Images", value=f"**{total}** images", inline=True)
        header.add_field(name="📊 Today", value=f"{self.hzone_count_today}/24", inline=True)
        header.set_footer(text="Sansa Bot • hentaidad.com")
        await channel.send(embed=header)

        for i, img_url in enumerate(images_to_post, 1):
            img_embed = discord.Embed(color=0xE91E63)
            img_embed.set_image(url=img_url)
            img_embed.set_footer(text=f"{post['character']}  •  {i}/{total}  •  hentaidad.com")
            await channel.send(embed=img_embed)

        log.info(f"✅ Auto hdad posted {total} images ({self.hzone_count_today}/24)")

    @auto_hdad.before_loop
    async def before_auto_hdad(self):
        await self.bot.wait_until_ready()

    # ── Auto Sakuh (sakuhentai.net) - Every Hour ───────
    @tasks.loop(hours=1)
    async def auto_sakuh(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        channel = self.bot.get_channel(SAKUH_CHANNEL_ID)
        if not channel:
            return

        sakuh_cog = self.bot.get_cog("Sakuh")
        if not sakuh_cog:
            return

        data = await sakuh_cog.fetch_next_sakuh_page()
        if not data or not data.get("images"):
            return

        page_num = data["page"]
        header = discord.Embed(
            title=f"🔞 Sakuhentai Gallery • Page {page_num}",
            url=data.get("list_url", ""),
            color=0xE91E63,
            timestamp=datetime.utcnow()
        )
        header.set_footer(text="Sansa Bot • sakuhentai.net • Serial")
        await channel.send(embed=header)

        total = len(data["images"])
        for i, item in enumerate(data["images"], 1):
            try:
                try:
                    nice_title = get_nice_title(item.get("page_url", ""))
                except Exception:
                    nice_title = f"Image {i}"
                embed = discord.Embed(
                    title=f"🖼️ {nice_title}",
                    url=item.get("page_url", data.get("list_url", "")),
                    color=0xE91E63
                )
                embed.set_image(url=item["img_url"])
                anime = get_anime_name(item.get("page_url", ""))
                embed.set_footer(text=anime)
                await channel.send(embed=embed)
            except discord.HTTPException as e:
                log.warning(f"Auto sakuh: Failed to send image {i}: {e} | URL: {item['img_url']}")
                continue

        log.info(f"✅ Auto sakuh posted page {page_num} ({total} images)")

    @auto_sakuh.before_loop
    async def before_auto_sakuh(self):
        await self.bot.wait_until_ready()

    # Auto Luci (lucioushentai.com) - Every Hour
    @tasks.loop(hours=1)
    async def auto_luci(self):
        await self.bot.wait_until_ready()
        self.check_reset()

        channel = self.bot.get_channel(LUCI_CHANNEL_ID)
        if not channel:
            return

        luci_cog = self.bot.get_cog("Luci")
        if not luci_cog:
            return

        post = await luci_cog.fetch_luci_post()
        if not post or not post.get("items"):
            return

        items = post["items"][:12]

        header = discord.Embed(
            title="🔞 LuciousHentai • 12 Random Characters",
            color=0xE91E63,
            timestamp=datetime.utcnow()
        )
        header.set_footer(text="Sansa Bot • lucioushentai.com")
        await channel.send(embed=header)

        for item in items:
            try:
                anime = get_anime_name(item["page_url"])
                img_embed = discord.Embed(
                    title=f"🖼️ {item['title']}",
                    url=item["page_url"],
                    color=0xE91E63
                )
                img_embed.set_image(url=item["img_url"])
                img_embed.set_footer(text=anime)
                await channel.send(embed=img_embed)
            except discord.HTTPException as e:
                log.warning(f"Auto luci image failed: {e}")
                continue

        log.info(f"✅ Auto luci posted 12 different characters")

    @auto_luci.before_loop
    async def before_auto_luci(self):
        await self.bot.wait_until_ready()

    @property
    def waifu_today(self):
        return self.waifu_count_today

    @property
    def anime_today(self):
        return self.anime_count_today

    @property
    def hanime_today(self):
        return self.hanime_count_today

    @property
    def hzone_today(self):
        return self.hzone_count_today


async def setup(bot):
    await bot.add_cog(Auto(bot))
