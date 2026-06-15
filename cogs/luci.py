import discord
from discord.ext import commands
from discord import app_commands
from bs4 import BeautifulSoup
import logging
import random
import asyncio
import functools
import cloudscraper
from config import LUCI_CHANNEL_ID, COLOR_ERROR

log = logging.getLogger("SansaBot.Luci")

LUCI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://lucioushentai.com/",
}

BASE_URL = "https://lucioushentai.com"


def _create_scraper():
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )


async def _cloud_get(url: str, headers: dict = None):
    loop = asyncio.get_event_loop()
    scraper = _create_scraper()

    def _sync_request():
        return scraper.get(url, headers=headers or {}, timeout=25)

    resp = await loop.run_in_executor(None, _sync_request)
    return resp


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
        return "LuciousHentai"
    except Exception:
        return "LuciousHentai"


class Luci(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Luci Cog loaded")

    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != LUCI_CHANNEL_ID:
            embed = discord.Embed(
                description=f"❌ This command only works in <#{LUCI_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def _get_post_links_from_page(self, page: int = 1):
        page_url = BASE_URL if page == 1 else f"{BASE_URL}/page/{page}/"

        for attempt in range(2):
            try:
                resp = await _cloud_get(page_url, LUCI_HEADERS)
                log.info(f"Luci page {page} status: {resp.status_code}")

                if resp.status_code != 200:
                    await asyncio.sleep(1)
                    continue

                html = resp.text
                soup = BeautifulSoup(html, "lxml")
                links = []
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("https://lucioushentai.com/"):
                        href = href.replace("https://lucioushentai.com", "")
                    if not href.startswith("/"):
                        continue
                    if (len(href) > 25 and
                        href.count("-") >= 3 and
                        not any(bad in href.lower() for bad in [
                            "page", "tag", "category", "search", "feed", "wp-",
                            "comment", "popular", "privacy", "policy", "content",
                            "terms", "about", "contact", "login", "register", "most-like"
                        ])):
                        if href not in links:
                            links.append(href)
                if links:
                    return links
            except Exception as e:
                log.warning(f"Luci page {page} attempt failed: {e}")
                await asyncio.sleep(1)
        return []

    async def fetch_luci_post(self):
        """Get 12 images from 12 completely different characters"""
        for attempt in range(6):
            try:
                all_links = []
                for _ in range(5):
                    rand_page = random.randint(1, 20)
                    links = await self._get_post_links_from_page(rand_page)
                    all_links.extend(links)

                unique_links = list(set(all_links))
                random.shuffle(unique_links)

                if len(unique_links) < 12:
                    continue

                selected_posts = unique_links[:12]
                results = []

                for post_path in selected_posts:
                    post_url = BASE_URL + post_path if post_path.startswith("/") else post_path

                    if any(bad in post_url.lower() for bad in ["policy", "privacy", "content"]):
                        continue

                    try:
                        resp = await _cloud_get(post_url, LUCI_HEADERS)
                        if resp.status_code != 200:
                            continue

                        html = resp.text
                        soup = BeautifulSoup(html, "lxml")

                        title_tag = soup.find("h1") or soup.find("title")
                        title = title_tag.get_text(strip=True) if title_tag else "Lucious Hentai"
                        title = title.split(" - ")[0].strip()[:70]

                        img_url = None
                        for img in soup.find_all("img"):
                            src = (img.get("src") or img.get("data-src") or "").strip()
                            if "img.lucioushentai.com/data/" in src:
                                if any(src.lower().endswith(ext) for ext in [".webp", ".jpg", ".jpeg", ".png"]):
                                    if "logo" not in src.lower():
                                        img_url = src
                                        break

                        if img_url:
                            results.append({
                                "img_url": img_url,
                                "page_url": post_url,
                                "title": title
                            })
                    except Exception:
                        continue

                    if len(results) >= 12:
                        break

                if len(results) >= 12:
                    return {"items": results}

            except Exception as e:
                log.warning(f"Luci fetch attempt {attempt+1} error: {e}")
                await asyncio.sleep(2)

        log.error("Luci: Failed to get 12 different characters")
        return None

    @app_commands.command(name="luci", description="Get 12 images from LuciousHentai")
    async def luci(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        post = await self.fetch_luci_post()

        if not post or not post.get("items"):
            embed = discord.Embed(
                description="❌ Failed to fetch from LuciousHentai. Try again.",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        items = post["items"][:12]

        header = discord.Embed(
            title="🔞 LuciousHentai • 12 Random Characters",
            color=0xE91E63
        )
        header.set_footer(text="Sansa Bot • lucioushentai.com")
        await interaction.followup.send(embed=header)

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
                await interaction.channel.send(embed=img_embed)
            except discord.HTTPException as e:
                log.warning(f"Luci image send failed: {e}")
                continue


async def setup(bot):
    await bot.add_cog(Luci(bot))