# ============================================
#   Sansa Bot — Memes Cog
#   Commands: /memes, /memes hot, /memes new, /memes funny
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import logging
import random
from config import (
    CHAT_CHANNEL_ID, COLOR_MEMES, COLOR_ERROR, REDDIT_SUBREDDITS
)

log = logging.getLogger("SansaBot.Memes")

class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Memes Cog loaded")

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

    # ── Meme Fetch ─────────────────────────
    async def fetch_meme(self, sort: str = "hot"):
        subreddit = random.choice(REDDIT_SUBREDDITS)
        url = f"https://meme-api.com/gimme/{subreddit}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "title": data.get("title", "Anime Meme"),
                            "url": data.get("url", ""),
                            "subreddit": data.get("subreddit", subreddit),
                            "author": data.get("author", "Unknown"),
                            "ups": data.get("ups", 0),
                            "post_link": data.get("postLink", "")
                        }
        except Exception as e:
            log.error(f"Meme fetch error: {e}")
        return None

    # ── Build Meme Embed ───────────────────
    def build_embed(self, meme: dict, label: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"{label} — {meme['title']}",
            color=COLOR_MEMES,
            url=meme["post_link"]
        )
        embed.set_image(url=meme["url"])
        embed.add_field(name="👤 Author", value=meme["author"], inline=True)
        embed.add_field(name="⬆️ Upvotes", value=str(meme["ups"]), inline=True)
        embed.add_field(name="📌 Subreddit", value=f"r/{meme['subreddit']}", inline=True)
        embed.set_footer(text="Sansa Bot 🌸 • Powered by Reddit")
        return embed

    # ── /memes ─────────────────────────────
    @app_commands.command(name="memes", description="😂 Show anime memes")
    @app_commands.describe(category="Meme category: hot, new, funny (defaults to random)")
    @app_commands.choices(category=[
        app_commands.Choice(name="🔥 Hot", value="hot"),
        app_commands.Choice(name="🆕 New", value="new"),
        app_commands.Choice(name="😂 Funny", value="funny"),
    ])
    async def memes(self, interaction: discord.Interaction, category: str = "hot"):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        label_map = {
            "hot": "🔥 Hot Meme",
            "new": "🆕 New Meme",
            "funny": "😂 Funny Meme"
        }
        label = label_map.get(category, "😂 Anime Meme")

        meme = await self.fetch_meme(sort=category)
        if not meme:
            embed = discord.Embed(
                description="❌ Failed to fetch meme. Please try again.",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        embed = self.build_embed(meme, label)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Memes(bot))
