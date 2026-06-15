# ============================================
#   Sansa Bot — Hanime Cog (NSFW)
#   Commands: /hanime
#   Auto posting handled in auto.py
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import logging
import random
import urllib.parse
from config import HANIME_CHANNEL_ID, COLOR_ERROR

log = logging.getLogger("SansaBot.Hanime")

# Popular hentai characters for random posts (better variety)
POPULAR_HENTAI_CHARACTERS = [
    "makima", "power", "zero_two", "marin_kitagawa", "raven", "hinata_hyuuga",
    "asuna_yuuki", "miku_nakano", "emilia", "rem_(re:zero)", "aqua_(konosuba)",
    "darkness", "megumin", "yor_forger", "anya_forger", "frieren", "fern",
    "mitsuri_kanroji", "shinobu_kocho", "nezuko_kamado", "hitori_gotou",
    "kobeni_higashiyama", "quanxi", "reze", "yoru", "himeno", "yor_forger",
    "fubuki", "tatsumaki", "2b", "a2", "vi", "jinx", "caitlyn", "ahri",
    "akali", "evelynn", "kda_ahri", "seraphine", "miss_fortune", "lux",
    "riven", "irelia", "katarina", "leona", "soraka", "syndra"
]

class Hanime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Hanime Cog loaded (NSFW)")

    async def check_channel(self, interaction: discord.Interaction) -> bool:
        # Only allow in #hanime channel (no separate chat channel needed)
        if interaction.channel_id != HANIME_CHANNEL_ID:
            embed = discord.Embed(
                description=f"❌ This command only works in <#{HANIME_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def fetch_hentai_images(self, character: str, limit: int = 10):
        """Fetch hentai using Nekobot (simple & more reliable on restricted hosts)"""
        images = []
        try:
            async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}) as session:
                for _ in range(limit):
                    async with session.get("https://nekobot.xyz/api/image?type=hentai", timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("success") and data.get("message"):
                                images.append({"url": data["message"]})
        except Exception as e:
            log.warning(f"Nekobot hentai fetch error: {e}")

        return images

    async def get_character_info(self, character: str):
        """Try to get short info from Jikan (MyAnimeList)"""
        encoded = urllib.parse.quote(character)
        url = f"https://api.jikan.moe/v4/characters?q={encoded}&limit=1"

        try:
            async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}) as session:
                async with session.get(url, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("data"):
                            char = data["data"][0]
                            about = char.get("about", "No description available.")[:300]
                            name = char.get("name", character.title())
                            return {
                                "name": name,
                                "about": about,
                                "image": char.get("images", {}).get("jpg", {}).get("image_url", "")
                            }
        except Exception as e:
            log.warning(f"Character info fetch failed: {e}")
        return None

    # ── /hanime ─────────────────────────────
    @app_commands.command(name="hanime", description="🔞 Get hentai images (12 images, NSFW)")
    @app_commands.describe(query="Character or anime name (optional)")
    async def hanime(self, interaction: discord.Interaction, query: str = None):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer(ephemeral=False)

        character = query or random.choice(POPULAR_HENTAI_CHARACTERS)

        images = await self.fetch_hentai_images(character, limit=10)

        if not images:
            embed = discord.Embed(
                description=f"❌ No results found for **{character}**. Try another name.",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        info = await self.get_character_info(character)

        # Main info embed
        main_embed = discord.Embed(
            title=f"🔞 {character.replace('_', ' ').title()}",
            color=0xFF69B4
        )

        if info:
            main_embed.add_field(name="📖 About", value=info["about"], inline=False)
            if info.get("image"):
                main_embed.set_thumbnail(url=info["image"])
        else:
            main_embed.add_field(name="📖 About", value="No character info available.", inline=False)

        main_embed.set_footer(text="Sansa Bot • NSFW • Nekobot")
        await interaction.followup.send(embed=main_embed)

        # Send 12 images (as separate embeds for better gallery view)
        for i, img in enumerate(images[:12], 1):
            embed = discord.Embed(color=0xFF69B4)
            embed.set_image(url=img["url"])
            embed.set_footer(text=f"Image {i}/12 • {character.replace('_', ' ').title()}")
            await interaction.channel.send(embed=embed)

    # ── Helper for auto posting ─────────────
    async def get_random_hentai_post(self):
        """Used by auto.py for hourly posting"""
        character = random.choice(POPULAR_HENTAI_CHARACTERS)
        images = await self.fetch_hentai_images(character, limit=12)

        if not images:
            return None

        info = await self.get_character_info(character)

        return {
            "character": character.replace("_", " ").title(),
            "images": images[:12],
            "info": info
        }


async def setup(bot):
    await bot.add_cog(Hanime(bot))
