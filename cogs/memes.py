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
        log.info(f"✅ Memes Cog loaded (CHAT_CHANNEL_ID={CHAT_CHANNEL_ID})")

    # ── Channel Check ──────────────────────
    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if CHAT_CHANNEL_ID == 0:
            log.error("[Memes] CHAT_CHANNEL_ID is 0 (not set in .env)!")
            await interaction.response.send_message("❌ Bot misconfigured: CHAT_CHANNEL_ID not set in .env", ephemeral=True)
            return False
        if interaction.channel_id != CHAT_CHANNEL_ID:
            ch = interaction.guild.get_channel(CHAT_CHANNEL_ID) if interaction.guild else None
            ch_name = ch.name if ch else "anime-chat"
            log.warning(f"[Memes] Blocked /memes from #{getattr(interaction.channel, 'name', 'unknown')} (need #{ch_name} id={CHAT_CHANNEL_ID})")
            embed = discord.Embed(
                description=f"❌ This command only works in <#{CHAT_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    # ── Meme Fetch ─────────────────────────
    async def fetch_meme(self, sort: str = "hot"):
        for attempt in range(3):
            subreddit = random.choice(REDDIT_SUBREDDITS)
            url = f"https://meme-api.com/gimme/{subreddit}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        log.info(f"[Memes] Attempt {attempt+1} from r/{subreddit} → status {resp.status}")
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("nsfw"):
                                log.info("[Memes] Got NSFW, retrying...")
                                continue
                            return {
                                "title": data.get("title", "Anime Meme"),
                                "url": data.get("url", ""),
                                "subreddit": data.get("subreddit", subreddit),
                                "author": data.get("author", "Unknown"),
                                "ups": data.get("ups", 0),
                                "post_link": data.get("postLink", "")
                            }
            except Exception as e:
                log.warning(f"[Memes] Fetch error from r/{subreddit}: {e}")
        log.error("[Memes] All meme sources failed after retries")
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
                description="❌ Failed to fetch meme (all sources down or NSFW filtered). Try again.",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=embed)
            return

        embed = self.build_embed(meme, label)
        await interaction.followup.send(embed=embed)
        log.info(f"[Memes] Posted /memes {category} from r/{meme['subreddit']}")


async def setup(bot):
    await bot.add_cog(Memes(bot))
    log.info("✅ Memes Cog setup complete (fetch from meme-api.com + NSFW retry)")
