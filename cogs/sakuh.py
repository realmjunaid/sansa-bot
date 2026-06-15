# ============================================
#   Sansa Bot — Sakuh (sakuhentai.net)
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from bs4 import BeautifulSoup
import logging
import json
import os
import random
import re
from urllib.parse import urljoin, urlparse
from config import SAKUH_CHANNEL_ID, COLOR_ERROR

log = logging.getLogger("SansaBot.Sakuh")

SAKUH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sakuhentai.net/",
}

BASE_URL = "https://www.sakuhentai.net"


def get_nice_title(url: str) -> str:
    if not url:
        return "Sakuhentai"
    try:
        slug = str(url).rstrip("/").split("/")[-1]
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
        }
        for key, name in anime_map.items():
            if key in slug:
                return name
        # Fallback: try last 2-3 words from slug
        parts = url.rstrip("/").split("/")[-1].split("-")
        if len(parts) >= 3:
            return " ".join(parts[-3:]).title()
        return "Sakuhentai"
    except Exception:
        return "Sakuhentai"


def is_valid_url(url: str) -> bool:
    """Check if a URL is well-formed and usable in Discord embeds."""
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc, result.path])
    except Exception:
        return False


class Sakuh(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state_file = "sakuh_state.json"
        self.max_page = 356
        self.min_page = 1
        self.start_page = 2
        self.current_page = self._load_current_page()
        if not os.path.exists(self.state_file):
            self._save_current_page(self.current_page)
        log.info("✅ Sakuh Cog loaded")

    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != SAKUH_CHANNEL_ID:
            embed = discord.Embed(
                description=f"❌ This command only works in <#{SAKUH_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    def _load_current_page(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    p = data.get("current_page", self.start_page)
                    if not isinstance(p, int) or p < self.min_page or p > self.max_page:
                        p = self.start_page
                    return p
        except Exception:
            pass
        return self.start_page

    def _save_current_page(self, page: int):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump({"current_page": page}, f, indent=2)
        except Exception:
            pass

    async def _scrape_sakuh_list_page(self, page: int):
        if page < 2:
            list_url = f"{BASE_URL}/hentai-gallery/"
        else:
            list_url = f"{BASE_URL}/hentai-gallery/page/{page}/"
        try:
            async with aiohttp.ClientSession(headers=SAKUH_HEADERS) as session:
                async with session.get(list_url, timeout=20) as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text()
                soup = BeautifulSoup(html, "lxml")
                gallery_links = []
                seen = set()
                for a in soup.find_all("a", href=True):
                    href = a.get("href", "").strip()
                    if not href.startswith("http"):
                        href = urljoin(BASE_URL, href)
                    if (
                        href.startswith(BASE_URL)
                        and "/hentai-gallery/" not in href
                        and "/page/" not in href
                        and "/feed/" not in href
                        and "hentai-gallery" in href
                        and href not in seen
                        and is_valid_url(href)
                    ):
                        seen.add(href)
                        gallery_links.append(href)
                images = []
                seen_imgs = set()
                for img in soup.find_all("img"):
                    src = (img.get("src") or img.get("data-src") or img.get("data-lazy-src") or "").strip()
                    if not src or "sakuhentai.net" not in src:
                        continue
                    if src.startswith("//"):
                        src = "https:" + src
                    elif not src.startswith("http"):
                        src = urljoin(BASE_URL, src)
                    if src in seen_imgs:
                        continue
                    if "/wp-content/uploads/" not in src:
                        continue
                    seen_imgs.add(src)
                    images.append(src)
                paired = []
                n = min(len(gallery_links), len(images))
                for i in range(n):
                    paired.append({"img_url": images[i], "page_url": gallery_links[i]})
                if not paired:
                    for img in images[:12]:
                        paired.append({"img_url": img, "page_url": list_url})
                return paired[:12]
        except Exception:
            return []

    async def fetch_next_sakuh_page(self):
        page = self.current_page
        items = await self._scrape_sakuh_list_page(page)
        nextp = page + 1
        if nextp > self.max_page:
            nextp = self.min_page
        self.current_page = nextp
        self._save_current_page(nextp)
        return {
            "page": page,
            "images": items,
            "list_url": f"{BASE_URL}/hentai-gallery/page/{page}/" if page >= 2 else f"{BASE_URL}/hentai-gallery/"
        }

    async def fetch_sakuh_same_character(self, count: int = 15):
        """
        Picks one random gallery and returns up to 'count' images from the same character.
        """
        try:
            async with aiohttp.ClientSession(headers=SAKUH_HEADERS) as session:

                # Try multiple pages until we get a valid gallery
                for attempt in range(5):
                    page = random.randint(1, 6)
                    list_url = f"{BASE_URL}/hentai-gallery/page/{page}/"

                    try:
                        async with session.get(list_url, timeout=15) as resp:
                            if resp.status != 200:
                                log.warning(f"List page {page} returned status {resp.status}")
                                continue
                            html = await resp.text()
                    except Exception as e:
                        log.warning(f"Failed to fetch list page: {e}")
                        continue

                    soup = BeautifulSoup(html, "lxml")

                    # Collect unique gallery links
                    gallery_links = []
                    seen_links = set()
                    for a in soup.select("a[href*='/hentai-gallery/']"):
                        href = a.get("href", "").strip()
                        # Make sure it's a full valid URL
                        if not href.startswith("http"):
                            href = urljoin(BASE_URL, href)
                        # Filter only gallery detail pages (not list pages)
                        if (
                            href.startswith(BASE_URL)
                            and "/hentai-gallery/" in href
                            and "/page/" not in href
                            and href not in seen_links
                            and is_valid_url(href)
                        ):
                            seen_links.add(href)
                            gallery_links.append(href)

                    if not gallery_links:
                        log.warning(f"No gallery links found on page {page}")
                        continue

                    # Choose one random gallery (same character)
                    chosen = random.choice(gallery_links)
                    log.info(f"Chosen gallery: {chosen}")

                    try:
                        async with session.get(chosen, timeout=15) as g_resp:
                            if g_resp.status != 200:
                                log.warning(f"Gallery page returned status {g_resp.status}")
                                continue
                            g_html = await g_resp.text()
                    except Exception as e:
                        log.warning(f"Failed to fetch gallery: {e}")
                        continue

                    g_soup = BeautifulSoup(g_html, "lxml")

                    # Get character/title name
                    title_tag = g_soup.find("h1")
                    character = title_tag.get_text(strip=True) if title_tag else "Sakuhentai"

                    # Extract images with their page links
                    images = []
                    seen_imgs = set()

                    for img in g_soup.select("img"):
                        src = (img.get("src") or img.get("data-src") or "").strip()

                        if not src:
                            continue

                        # Make absolute URL if needed
                        if src.startswith("//"):
                            src = "https:" + src
                        elif not src.startswith("http"):
                            src = urljoin(BASE_URL, src)

                        # Only keep sakuhentai images
                        if "sakuhentai.net" not in src:
                            continue

                        # Try to get full resolution (remove thumbnail sizing)
                        full = src
                        for pattern in ["-300x", "-600x", "-150x", "-768x", "-1024x"]:
                            if pattern in full:
                                # Remove the resize suffix like -300x200
                                import re
                                full = re.sub(r'-\d+x\d+', '', full)
                                break

                        if full in seen_imgs:
                            continue
                        if not is_valid_url(full):
                            log.warning(f"Skipping invalid image URL: {full}")
                            continue

                        seen_imgs.add(full)

                        # Try to find parent <a> tag for the image page link
                        parent_a = img.find_parent("a")
                        if parent_a:
                            page_link = parent_a.get("href", "").strip()
                            if not page_link.startswith("http"):
                                page_link = urljoin(BASE_URL, page_link)
                            if not is_valid_url(page_link):
                                page_link = chosen
                        else:
                            page_link = chosen

                        images.append({
                            "img_url": full,
                            "page_url": page_link
                        })

                    if len(images) < 5:
                        log.warning(f"Not enough images found ({len(images)}), retrying...")
                        continue

                    random.shuffle(images)
                    selected = images[:count]

                    log.info(f"✅ Sakuh: {character} — {len(selected)} images ready")
                    return {
                        "character": character,
                        "images": selected,
                        "source_url": chosen
                    }

                # All attempts failed
                log.error("Sakuh: All 5 attempts failed")
                return None

        except Exception as e:
            log.warning(f"Sakuh same-character error: {e}")
            return None

    # ── /saku Command ───────────────────────
    @app_commands.command(name="saku", description="Get next 12 images from Sakuhentai hentai-gallery (serial)")
    async def saku(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        data = await self.fetch_next_sakuh_page()

        if not data or not data.get("images"):
            embed = discord.Embed(
                description="❌ Failed to fetch from Sakuhentai. Please try again.",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        page_num = data["page"]
        header = discord.Embed(
            title=f"🔞 Sakuhentai Gallery • Page {page_num}",
            url=data.get("list_url", ""),
            color=0xE91E63
        )
        header.set_footer(text="Sansa Bot • sakuhentai.net • Serial")
        await interaction.followup.send(embed=header)

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
                await interaction.channel.send(embed=embed)
            except discord.HTTPException as e:
                log.warning(f"Failed to send image {i}: {e} | URL: {item['img_url']}")
                continue


async def setup(bot):
    await bot.add_cog(Sakuh(bot))
