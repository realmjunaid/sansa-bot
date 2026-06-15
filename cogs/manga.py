# ============================================
#   Sansa Bot — Manga Cog
#   Commands: /manga, /manga <title>
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import logging
import random
from config import (
    CHAT_CHANNEL_ID, COLOR_MANGA, COLOR_ERROR
)

log = logging.getLogger("SansaBot.Manga")

# ── AniList Queries ────────────────────────
SEARCH_MANGA_QUERY = """
query ($search: String) {
  Media(search: $search, type: MANGA) {
    id
    title { romaji english }
    description(asHtml: false)
    chapters
    volumes
    averageScore
    genres
    status
    startDate { year month day }
    coverImage { extraLarge }
    siteUrl
    staff {
      edges {
        role
        node { name { full } }
      }
    }
  }
}
"""

RANDOM_MANGA_QUERY = """
query ($page: Int) {
  Page(page: $page, perPage: 1) {
    media(type: MANGA, sort: POPULARITY_DESC, status: FINISHED) {
      id
      title { romaji english }
      description(asHtml: false)
      chapters
      volumes
      averageScore
      genres
      startDate { year }
      coverImage { extraLarge }
      siteUrl
    }
  }
}
"""

class Manga(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Manga Cog loaded")

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

    # ── AniList Request ────────────────────
    async def anilist_request(self, query: str, variables: dict = {}):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://graphql.anilist.co",
                    json={"query": query, "variables": variables},
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            log.error(f"AniList request error: {e}")
        return None

    # ── /manga ─────────────────────────────
    @app_commands.command(name="manga", description="📚 Get details for a random or specific manga")
    @app_commands.describe(title="Manga title (leave empty for random)")
    async def manga(self, interaction: discord.Interaction, title: str = None):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        if title:
            # Specific manga search
            data = await self.anilist_request(SEARCH_MANGA_QUERY, {"search": title})
            if not data or not data.get("data", {}).get("Media"):
                embed = discord.Embed(
                    description=f"❌ No manga found with the name **{title}**!",
                    color=COLOR_ERROR
                )
                await interaction.followup.send(embed=embed)
                return

            manga = data["data"]["Media"]

            desc = manga.get("description", "No description available.")
            if desc and len(desc) > 350:
                desc = desc[:350] + "..."

            genres = ", ".join(manga.get("genres", [])[:4]) or "Unknown"
            title_en = manga["title"].get("english") or manga["title"].get("romaji", "Unknown")
            title_jp = manga["title"].get("romaji", "")

            # Author
            author = "Unknown"
            staff_edges = manga.get("staff", {}).get("edges", [])
            for edge in staff_edges:
                if "Story" in edge.get("role", "") or "Art" in edge.get("role", ""):
                    author = edge["node"]["name"]["full"]
                    break

            # Status
            status_map = {
                "FINISHED": "✅ Finished",
                "RELEASING": "📡 Ongoing",
                "NOT_YET_RELEASED": "🔜 Upcoming",
                "CANCELLED": "❌ Cancelled",
                "HIATUS": "⏸️ Hiatus"
            }
            status = status_map.get(manga.get("status", ""), "Unknown")

            sd = manga.get("startDate", {})
            air_date = f"{sd.get('day', '?')}/{sd.get('month', '?')}/{sd.get('year', '?')}"

            embed = discord.Embed(
                title=f"📚 {title_en}",
                description=f"*{title_jp}*\n\n{desc}",
                color=COLOR_MANGA,
                url=manga.get("siteUrl", "")
            )
            embed.add_field(name="⭐ Score", value=f"{manga.get('averageScore', 'N/A')}/100", inline=True)
            embed.add_field(name="📖 Chapters", value=str(manga.get("chapters", "N/A")), inline=True)
            embed.add_field(name="📦 Volumes", value=str(manga.get("volumes", "N/A")), inline=True)
            embed.add_field(name="📊 Status", value=status, inline=True)
            embed.add_field(name="✍️ Author", value=author, inline=True)
            embed.add_field(name="📅 Started", value=air_date, inline=True)
            embed.add_field(name="🎭 Genres", value=genres, inline=False)
            embed.set_image(url=manga["coverImage"]["extraLarge"])
            embed.set_footer(text="Sansa Bot 🌸 • Powered by AniList")

        else:
            # Random manga
            page = random.randint(1, 30)
            data = await self.anilist_request(RANDOM_MANGA_QUERY, {"page": page})
            if not data:
                embed = discord.Embed(
                    description="❌ Failed to fetch manga. Please try again.",
                    color=COLOR_ERROR
                )
                await interaction.followup.send(embed=embed)
                return

            manga = data["data"]["Page"]["media"][0]

            desc = manga.get("description", "No description.")
            if desc and len(desc) > 350:
                desc = desc[:350] + "..."

            genres = ", ".join(manga.get("genres", [])[:4]) or "Unknown"
            title_en = manga["title"].get("english") or manga["title"].get("romaji", "Unknown")
            title_jp = manga["title"].get("romaji", "")

            embed = discord.Embed(
                title=f"🎲 Random Manga — {title_en}",
                description=f"*{title_jp}*\n\n{desc}",
                color=COLOR_MANGA,
                url=manga.get("siteUrl", "")
            )
            embed.add_field(name="⭐ Score", value=f"{manga.get('averageScore', 'N/A')}/100", inline=True)
            embed.add_field(name="📖 Chapters", value=str(manga.get("chapters", "N/A")), inline=True)
            embed.add_field(name="📦 Volumes", value=str(manga.get("volumes", "N/A")), inline=True)
            embed.add_field(name="📅 Year", value=str(manga.get("startDate", {}).get("year", "N/A")), inline=True)
            embed.add_field(name="🎭 Genres", value=genres, inline=False)
            embed.set_image(url=manga["coverImage"]["extraLarge"])
            embed.set_footer(text="Sansa Bot 🌸 • Powered by AniList")

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Manga(bot))
