# ============================================
#   Sansa Bot — Sticky (stickyhentai.com)
#   Auto post + /sticky command in the same channel
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from bs4 import BeautifulSoup
import logging
import random
import re
from urllib.parse import quote
import cloudscraper
import asyncio
from config import STICKY_CHANNEL_ID, COLOR_ERROR

log = logging.getLogger("SansaBot.Sticky")

STICKY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://stickyhentai.com/",
}

BASE_URL = "https://stickyhentai.com"


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


class Sticky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Sticky Cog loaded (stickyhentai.com only)")

    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != STICKY_CHANNEL_ID:
            embed = discord.Embed(
                description=f"❌ This command only works in <#{STICKY_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def _parse_gallery_page(self, html: str, source_url: str):
        """Extract title + image urls from a stickyhentai gallery page."""
        soup = BeautifulSoup(html, "lxml")

        # Title from <title> or h1
        title_tag = soup.find("title") or soup.find("h1")
        raw_title = title_tag.get_text(strip=True) if title_tag else "Unknown Hentai"

        # Clean title
        character = re.sub(r'\s*\|\s*One Piece Hentai.*$', '', raw_title, flags=re.IGNORECASE)
        character = re.sub(r'\s*\|\s*Stickyhentai.*$', '', character, flags=re.IGNORECASE)
        character = re.sub(r'\s+', ' ', character).strip()[:80]
        if not character:
            character = "Unknown Hentai"

        # Collect high quality images from cdn
        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if "cdn.stickyhentai.com/uploads/" in src:
                if src.startswith("//"):
                    src = "https:" + src
                elif not src.startswith("http"):
                    src = BASE_URL + src
                if src not in images and src.endswith((".webp", ".jpg", ".jpeg", ".png")):
                    images.append(src)

        # Also regex direct links in case
        if len(images) < 5:
            for m in re.finditer(r'https?://cdn\.stickyhentai\.com/uploads/[^"\'\s<>]+\.(?:webp|jpg|jpeg|png)', html, re.I):
                u = m.group(0)
                if u not in images:
                    images.append(u)

        if len(images) < 5:
            return None, None

        random.shuffle(images)
        return character, images[:15]

    async def scrape_random_gallery(self):
        """Pick random gallery from /hentai list and scrape."""
        try:
            # Get list page
            resp = await _cloud_get(f"{BASE_URL}/hentai", STICKY_HEADERS)
            if resp.status_code != 200:
                log.warning(f"Sticky list status: {resp.status_code}")
                return None

            html = resp.text
            soup = BeautifulSoup(html, "lxml")

            gallery_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("/hentai/") and len(href) > 10 and "-hentai" in href.lower():
                    full = BASE_URL + href if not href.startswith("http") else href
                    if full not in gallery_links:
                        gallery_links.append(full)

            if not gallery_links:
                # fallback to home
                resp = await _cloud_get(BASE_URL, STICKY_HEADERS)
                if resp.status_code == 200:
                    html = resp.text
                    for m in re.finditer(r'href=["\'](/hentai/[^"\']+?)["\']', html, re.I):
                        full = BASE_URL + m.group(1)
                        if full not in gallery_links and len(full) > 20:
                            gallery_links.append(full)

            if not gallery_links:
                return None

            random.shuffle(gallery_links)
            for gal_url in gallery_links[:5]:
                g_resp = await _cloud_get(gal_url, STICKY_HEADERS)
                if g_resp.status_code != 200:
                    continue
                g_html = g_resp.text
                character, images = await self._parse_gallery_page(g_html, gal_url)
                if images and len(images) >= 5:
                    return {
                        "character": character,
                        "images": images,
                        "source_url": gal_url
                    }
            return None
        except Exception as e:
            log.warning(f"Sticky random scrape error: {e}")
            return None

    async def scrape_by_query(self, query: str):
        """Try to find gallery by searching via category or simple match."""
        try:
            q = quote(query.strip())
            search_url = f"{BASE_URL}/hentai?search={q}"  # may not exist, try anime tag fallback
            # Fallback strategy: visit /anime/{slug} or just scrape /hentai and match text

            resp = await _cloud_get(f"{BASE_URL}/hentai", STICKY_HEADERS)
            if resp.status_code != 200:
                return None
            html = resp.text

            soup = BeautifulSoup(html, "lxml")
            candidates = []
            q_lower = query.lower()

            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = (a.get_text() or "").lower()
                if not href.startswith("/hentai/"):
                    continue
                score = 0
                if q_lower in href.lower():
                    score += 3
                if q_lower in text:
                    score += 4
                if score > 0:
                    candidates.append((score, BASE_URL + href))

            candidates.sort(reverse=True)
            for _, gal_url in candidates[:3]:
                g_resp = await _cloud_get(gal_url, STICKY_HEADERS)
                if g_resp.status_code != 200:
                    continue
                character, images = await self._parse_gallery_page(g_resp.text, gal_url)
                if images and len(images) >= 5:
                    return {
                        "character": character,
                        "images": images,
                        "source_url": gal_url
                    }
            return None
        except Exception as e:
            log.warning(f"Sticky search error: {e}")
            return None

    async def get_random_sticky_post(self):
        return await self.scrape_random_gallery()

    # ── /sticky Command ───────────────────────
    @app_commands.command(name="sticky", description="🔞 Get random hentai images (stickyhentai.com)")
    @app_commands.describe(query="Character or title (optional)")
    async def sticky(self, interaction: discord.Interaction, query: str = None):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        if query:
            post = await self.scrape_by_query(query)
        else:
            post = await self.get_random_sticky_post()

        if not post or not post.get("images"):
            embed = discord.Embed(
                description="❌ No results found. Try a different name or try again.",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        total = len(post["images"][:15])

        main_embed = discord.Embed(
            title=f"🔞 {post['character']}",
            color=0xE91E63
        )
        main_embed.add_field(
            name="🔗 Source",
            value=post.get("source_url", "https://stickyhentai.com"),
            inline=False
        )
        main_embed.add_field(
            name="📸 Images",
            value=f"**{total}** images",
            inline=True
        )
        main_embed.set_footer(text="Sansa Bot • stickyhentai.com")
        await interaction.followup.send(embed=main_embed)

        for i, img_url in enumerate(post["images"][:15], 1):
            img_embed = discord.Embed(color=0xE91E63)
            img_embed.set_image(url=img_url)
            img_embed.set_footer(text=f"{post['character']}  •  {i}/{total}  •  stickyhentai.com")
            await interaction.channel.send(embed=img_embed)


async def setup(bot):
    await bot.add_cog(Sticky(bot))
