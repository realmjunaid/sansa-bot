# ============================================
#   Sansa Bot — Hdad (hentaidad.com only)
#   Auto post + /hdad command in the same channel
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
from config import HDAD_CHANNEL_ID, COLOR_ERROR

log = logging.getLogger("SansaBot.Hentaidad")

HZONE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}



class Hentaidad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Hdad Cog loaded (hentaidad only)")

    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != HDAD_CHANNEL_ID:
            embed = discord.Embed(
                description=f"❌ This command only works in <#{HDAD_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def _parse_gallery_page(self, html: str, source_url: str):
        """Use BeautifulSoup to extract character name and high-quality images from a gallery page."""
        soup = BeautifulSoup(html, "lxml")

        # Get character name from h1 or title
        title_tag = soup.find("h1") or soup.find("title")
        raw_title = title_tag.get_text(strip=True) if title_tag else "Unknown Hentai"

        # Clean the title nicely
        character = re.sub(r'^\[Premium\s*\d+p?\]\s*', '', raw_title, flags=re.IGNORECASE)
        character = re.sub(r'\s+', ' ', character).strip()[:80]
        if " - " in character:
            character = character.split(" - ")[0].strip()
        if "#" in character:
            character = character.split("#")[0].strip()
        if not character:
            character = "Unknown Hentai"

        # Extract images - prefer high resolution ones
        images = []

        # Method 1: Direct <img> tags in content/images
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
            if "/content/images/" in src and any(src.lower().endswith(ext) for ext in [".webp", ".jpg", ".jpeg", ".png"]):
                if not src.startswith("http"):
                    src = "https://hentaidad.com" + src
                if src not in images:
                    images.append(src)

        # Method 2: Look for links to full images
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/content/images/" in href and any(href.lower().endswith(ext) for ext in [".webp", ".jpg", ".jpeg", ".png"]):
                if not href.startswith("http"):
                    href = "https://hentaidad.com" + href
                if href not in images:
                    images.append(href)

        if len(images) < 5:
            return None, None

        random.shuffle(images)
        return character, images[:15]

    async def scrape_random_gallery(self):
        """Scrape random gallery using BeautifulSoup."""
        try:
            async with aiohttp.ClientSession(headers=HZONE_HEADERS) as session:
                async with session.get("https://hentaidad.com/random", timeout=15) as resp:
                    if resp.status != 200:
                        log.warning(f"Random page status: {resp.status}")
                        return None
                    html = await resp.text()
                    source_url = str(resp.url)

                character, images = await self._parse_gallery_page(html, source_url)
                if not images:
                    return None

                return {
                    "character": character,
                    "images": images,
                    "source_url": source_url
                }
        except Exception as e:
            log.warning(f"Hentaidad random scrape error: {e}")
            return None

    async def scrape_by_query(self, query: str):
        """
        Advanced search using BeautifulSoup.
        Matches query in both gallery URL and visible title text.
        """
        try:
            encoded = quote(query.strip())
            search_url = f"https://hentaidad.com/?q={encoded}"
            query_lower = query.lower().strip()

            async with aiohttp.ClientSession(headers=HZONE_HEADERS) as session:
                async with session.get(search_url, timeout=15) as resp:
                    if resp.status != 200:
                        return None
                    html = await resp.text()

                soup = BeautifulSoup(html, "lxml")

                candidates = []

                # Find all gallery links with their visible text
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    text = a.get_text(strip=True).lower()

                    # Skip non-gallery pages
                    if any(bad in href.lower() for bad in ["/categories", "/tag/", "/login", "/register", "/search", "/activity"]):
                        continue
                    if len(href) < 12 or not href.startswith("/"):
                        continue

                    # Score based on match in URL or title text
                    score = 0
                    if query_lower in href.lower():
                        score += 3
                    if query_lower in text:
                        score += 4

                    if score > 0:
                        candidates.append((score, href, text))

                if not candidates:
                    return None

                # Sort by score (best matches first)
                candidates.sort(reverse=True)

                # Try top 3 candidates
                for score, href, text in candidates[:3]:
                    gallery_url = "https://hentaidad.com" + href

                    async with session.get(gallery_url, timeout=15) as g_resp:
                        if g_resp.status != 200:
                            continue
                        g_html = await g_resp.text()

                    character, images = await self._parse_gallery_page(g_html, gallery_url)
                    if images and len(images) >= 5:
                        return {
                            "character": character,
                            "images": images,
                            "source_url": gallery_url
                        }

                return None
        except Exception as e:
            log.warning(f"Hentaidad search error: {e}")
            return None

    async def get_random_hzone_post(self):
        """Get 15 random images from hentaidad.com only"""
        return await self.scrape_random_gallery()

    async def get_random_hzone_post(self):
        """Get 15 random images from hentaidad.com only"""
        return await self.scrape_random_gallery()

    # ── /hdad Command ───────────────────────
    @app_commands.command(name="hdad", description="🔞 Get random hentai images (hentaidad.com)")
    @app_commands.describe(query="Character or title (optional)")
    async def hdad(self, interaction: discord.Interaction, query: str = None):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        if query:
            post = await self.scrape_by_query(query)
        else:
            post = await self.get_random_hzone_post()

        if not post or not post.get("images"):
            embed = discord.Embed(
                description="❌ No results found. Try a different name or try again.",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        total = len(post["images"][:15])

        # Beautiful main embed
        main_embed = discord.Embed(
            title=f"🔞 {post['character']}",
            color=0xE91E63
        )
        main_embed.add_field(
            name="🔗 Source",
            value=post.get("source_url", "https://hentaidad.com"),
            inline=False
        )
        main_embed.add_field(
            name="📸 Images",
            value=f"**{total}** images",
            inline=True
        )
        main_embed.set_footer(text="Sansa Bot • hentaidad.com")
        await interaction.followup.send(embed=main_embed)

        # Send 15 images with nice numbering
        for i, img_url in enumerate(post["images"][:15], 1):
            img_embed = discord.Embed(color=0xE91E63)
            img_embed.set_image(url=img_url)
            img_embed.set_footer(text=f"{post['character']}  •  {i}/{total}  •  hentaidad.com")
            await interaction.channel.send(embed=img_embed)


async def setup(bot):
    await bot.add_cog(Hentaidad(bot))
