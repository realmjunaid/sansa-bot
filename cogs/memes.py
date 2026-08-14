# ============================================
#   Sansa Bot — Memes Cog
#   Commands: /memes, /memes hot, /memes new, /memes funny
#   API: https://meme-api.com/gimme/{subreddit}
#   Note: 2nd path segment is COUNT only — not sort (hot/new break with 400)
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

# Category → preferred subreddits (meme-api has no hot/new sort)
CATEGORY_SUBS = {
    "hot": ["animememes", "goodanimemes", "anime_irl"],
    "new": ["animememes", "goodanimemes", "animefunny"],
    "funny": ["animefunny", "animememes", "goodanimemes"],
    "random": list(REDDIT_SUBREDDITS) + ["anime_irl", "Animemes"],
}

HEADERS = {
    "User-Agent": "SansaBot/1.0 (Discord anime meme bot)",
    "Accept": "application/json",
}


class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info(f"✅ Memes Cog loaded (CHAT_CHANNEL_ID={CHAT_CHANNEL_ID})")

    # ── Channel Check ──────────────────────
    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if CHAT_CHANNEL_ID == 0:
            log.error("[Memes] CHAT_CHANNEL_ID is 0 (not set in .env)!")
            await interaction.response.send_message(
                "❌ Bot misconfigured: CHAT_CHANNEL_ID not set in .env", ephemeral=True
            )
            return False
        if interaction.channel_id != CHAT_CHANNEL_ID:
            ch = interaction.guild.get_channel(CHAT_CHANNEL_ID) if interaction.guild else None
            ch_name = ch.name if ch else "anime-chat"
            log.warning(
                f"[Memes] Blocked /memes from #{getattr(interaction.channel, 'name', 'unknown')} "
                f"(need #{ch_name} id={CHAT_CHANNEL_ID})"
            )
            embed = discord.Embed(
                description=f"❌ This command only works in <#{CHAT_CHANNEL_ID}>!",
                color=COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    def _subs_for(self, category: str) -> list:
        key = (category or "hot").lower()
        if key not in CATEGORY_SUBS:
            key = "random"
        base = list(CATEGORY_SUBS[key])
        # shuffle copy so retries hit different subs
        random.shuffle(base)
        # also mix config list
        extra = [s for s in REDDIT_SUBREDDITS if s not in base]
        random.shuffle(extra)
        return base + extra

    # ── Meme Fetch ─────────────────────────
    async def fetch_meme(self, sort: str = "hot"):
        """
        Fetch one SFW meme.
        `sort` is only used to pick subreddit pool (API has no real sort).
        Correct URL: https://meme-api.com/gimme/{subreddit}
        """
        subs = self._subs_for(sort)
        timeout = aiohttp.ClientTimeout(total=12)

        async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
            for attempt, subreddit in enumerate(subs[:8], start=1):
                url = f"https://meme-api.com/gimme/{subreddit}"
                try:
                    async with session.get(url) as resp:
                        log.info(f"[Memes] Attempt {attempt} r/{subreddit} → {resp.status}")
                        if resp.status != 200:
                            text = await resp.text()
                            log.warning(f"[Memes] Bad status {resp.status}: {text[:120]}")
                            continue
                        data = await resp.json()
                        if not isinstance(data, dict):
                            continue
                        if data.get("nsfw") or data.get("spoiler"):
                            log.info("[Memes] NSFW/spoiler skipped, retry...")
                            continue
                        img = data.get("url") or ""
                        if not img:
                            continue
                        # Prefer image hosts Discord embeds well
                        lower = img.lower()
                        if not any(
                            lower.endswith(ext) or f".{ext}?" in lower
                            for ext in ("jpg", "jpeg", "png", "gif", "webp")
                        ) and "i.redd.it" not in lower and "i.imgur.com" not in lower:
                            # still allow; reddit gallery links often fail embed
                            if "v.redd.it" in lower or "gallery" in lower:
                                log.info(f"[Memes] Skip non-embed media: {img[:80]}")
                                continue
                        return {
                            "title": data.get("title") or "Anime Meme",
                            "url": img,
                            "subreddit": data.get("subreddit") or subreddit,
                            "author": data.get("author") or "Unknown",
                            "ups": data.get("ups") or 0,
                            "post_link": data.get("postLink") or "",
                        }
                except Exception as e:
                    log.warning(f"[Memes] Fetch error r/{subreddit}: {e}")

            # Last resort: generic gimme (any subreddit)
            try:
                async with session.get("https://meme-api.com/gimme") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, dict) and data.get("url") and not data.get("nsfw"):
                            return {
                                "title": data.get("title") or "Meme",
                                "url": data["url"],
                                "subreddit": data.get("subreddit") or "memes",
                                "author": data.get("author") or "Unknown",
                                "ups": data.get("ups") or 0,
                                "post_link": data.get("postLink") or "",
                            }
            except Exception as e:
                log.warning(f"[Memes] Generic gimme failed: {e}")

        log.error("[Memes] All meme sources failed after retries")
        return None

    # ── Build Meme Embed ───────────────────
    def build_embed(self, meme: dict, label: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"{label} — {meme['title']}"[:256],
            color=COLOR_MEMES,
            url=meme.get("post_link") or None,
        )
        embed.set_image(url=meme["url"])
        embed.add_field(name="👤 Author", value=str(meme.get("author", "Unknown"))[:100], inline=True)
        embed.add_field(name="⬆️ Upvotes", value=str(meme.get("ups", 0)), inline=True)
        embed.add_field(name="📌 Subreddit", value=f"r/{meme.get('subreddit', '?')}", inline=True)
        embed.set_footer(text="Sansa Bot 🌸 • Powered by Reddit")
        return embed

    # ── /memes ─────────────────────────────
    @app_commands.command(name="memes", description="😂 Show anime memes")
    @app_commands.describe(category="Meme category: hot, new, funny (defaults to hot)")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="🔥 Hot", value="hot"),
            app_commands.Choice(name="🆕 New", value="new"),
            app_commands.Choice(name="😂 Funny", value="funny"),
        ]
    )
    async def memes(self, interaction: discord.Interaction, category: str = "hot"):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        label_map = {
            "hot": "🔥 Hot Meme",
            "new": "🆕 New Meme",
            "funny": "😂 Funny Meme",
        }
        label = label_map.get(category, "😂 Anime Meme")

        meme = await self.fetch_meme(sort=category)
        if not meme:
            embed = discord.Embed(
                description="❌ Failed to fetch meme. Try again in a moment.",
                color=COLOR_ERROR,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = self.build_embed(meme, label)
        await interaction.followup.send(embed=embed)
        log.info(f"[Memes] Posted /memes {category} from r/{meme['subreddit']}")


async def setup(bot):
    await bot.add_cog(Memes(bot))
    log.info("✅ Memes Cog setup complete (meme-api.com/gimme/{sub})")
