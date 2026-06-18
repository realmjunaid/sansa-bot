# ============================================
#   Sansa Bot — Episode Alerts Cog
#   Tracking + auto alerts for airing anime
# ============================================

import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import logging
import json
import os
from datetime import datetime
from config import (
    CHAT_CHANNEL_ID, ANIME_UPDATES_CHANNEL_ID,
    COLOR_ANIME, COLOR_ERROR
)

log = logging.getLogger("SansaBot.Alerts")

ALERTS_FILE = "alerts.json"

# ── AniList Queries ────────────────────────
SEARCH_ANIME_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title { romaji english }
    episodes
    averageScore
    status
    season
    seasonYear
    nextAiringEpisode { episode airingAt timeUntilAiring }
    coverImage { extraLarge }
    siteUrl
  }
}
"""

DETAIL_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title { romaji english }
    episodes
    averageScore
    status
    season
    seasonYear
    nextAiringEpisode { episode airingAt timeUntilAiring }
    coverImage { extraLarge }
    siteUrl
  }
}
"""

TRENDING_QUERY = """
query ($season: MediaSeason, $year: Int) {
  Page(page: 1, perPage: 10) {
    media(type: ANIME, season: $season, seasonYear: $year, sort: POPULARITY_DESC) {
      id
      title { romaji english }
      averageScore
      episodes
      status
      season
      seasonYear
      coverImage { large }
      siteUrl
    }
  }
}
"""

class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracked = {}  # user_id str -> list of anime dicts
        self.last_weekly = None
        self.load_data()
        if ANIME_UPDATES_CHANNEL_ID != 0:
            self.check_episodes.start()
            self.check_new_seasons.start()
            self.weekly_report.start()
        else:
            log.warning("ANIME_UPDATES_CHANNEL_ID=0, alert tasks disabled")
        log.info("✅ Alerts Cog loaded")

    def cog_unload(self):
        self.check_episodes.cancel()
        self.check_new_seasons.cancel()
        self.weekly_report.cancel()

    # ── Persistence ────────────────────────
    def load_data(self):
        if os.path.exists(ALERTS_FILE):
            try:
                with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tracked = data.get("tracked", {})
            except Exception as e:
                log.error(f"Failed load alerts: {e}")
                self.tracked = {}
        else:
            self.tracked = {}

    def save_data(self):
        try:
            with open(ALERTS_FILE, "w", encoding="utf-8") as f:
                json.dump({"tracked": self.tracked}, f, indent=2)
        except Exception as e:
            log.error(f"Save alerts failed: {e}")

    # ── Channel Checks ─────────────────────
    async def check_chat(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != CHAT_CHANNEL_ID:
            embed = discord.Embed(
                description=f"❌ This command only works in <#{CHAT_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    # ── AniList Fetch ──────────────────────
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
            log.error(f"AniList error: {e}")
        return None

    async def fetch_anime_by_name(self, name: str):
        data = await self.anilist_request(SEARCH_ANIME_QUERY, {"search": name})
        if data and data.get("data", {}).get("Media"):
            return data["data"]["Media"]
        return None

    async def fetch_anime_by_id(self, aid: int):
        data = await self.anilist_request(DETAIL_QUERY, {"id": aid})
        if data and data.get("data", {}).get("Media"):
            return data["data"]["Media"]
        return None

    async def fetch_trending(self):
        from datetime import datetime as dt
        now = dt.utcnow()
        month = now.month
        year = now.year
        season_map = {
            (12, 1, 2): "WINTER", (3, 4, 5): "SPRING",
            (6, 7, 8): "SUMMER", (9, 10, 11): "FALL"
        }
        season = "WINTER"
        for m, s in season_map.items():
            if month in m:
                season = s
                break
        data = await self.anilist_request(TRENDING_QUERY, {"season": season, "year": year})
        if data and data.get("data", {}).get("Page"):
            return data["data"]["Page"]["media"]
        return []

    def get_season_str(self, media: dict) -> str:
        season = media.get("season")
        year = media.get("seasonYear")
        if season and year:
            return f"{season.capitalize()} {year}"
        return None

    def build_universal_embed(self, media: dict, extra: dict = None) -> discord.Embed:
        title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji", "Unknown")
        season_str = self.get_season_str(media)
        ep = media.get("episodes") or (extra or {}).get("ep", "?")
        status = media.get("status", "Unknown")
        score = media.get("averageScore", "N/A")
        cover = media.get("coverImage", {}).get("extraLarge") or media.get("coverImage", {}).get("large")
        site = media.get("siteUrl", "")

        # next ep info
        next_info = ""
        if extra:
            if extra.get("next_ep"):
                next_info = f"⏭️ Next Episode: {extra['next_ep']}\n"
            if extra.get("airing_in"):
                next_info += f"🕒 {extra['airing_in']}\n"

        embed = discord.Embed(
            title=f"📺 {title}",
            color=COLOR_ANIME,
            url=site
        )
        if season_str:
            embed.add_field(name="🎭 Season", value=season_str, inline=True)
        embed.add_field(name="🎬 Episode", value=str(ep), inline=True)
        embed.add_field(name="📡 Status", value=status, inline=True)
        if next_info:
            embed.add_field(name="Next", value=next_info, inline=False)
        if score and score != "N/A":
            embed.add_field(name="⭐ Score", value=f"{score}/100", inline=True)
        if cover:
            embed.set_image(url=cover)
        return embed

    # ── Commands ───────────────────────────
    @app_commands.command(name="epalert", description="Add anime to your episode tracking list")
    @app_commands.describe(anime="Anime name")
    async def epalert(self, interaction: discord.Interaction, anime: str):
        if not await self.check_chat(interaction):
            return
        await interaction.response.defer()

        media = await self.fetch_anime_by_name(anime)
        if not media:
            await interaction.followup.send(embed=discord.Embed(description=f"❌ Anime **{anime}** not found.", color=COLOR_ERROR))
            return

        uid = str(interaction.user.id)
        if uid not in self.tracked:
            self.tracked[uid] = []

        # avoid dup by id
        aid = media["id"]
        for t in self.tracked[uid]:
            if t.get("id") == aid:
                await interaction.followup.send("Already tracking.")
                return

        # init record
        next_ep = None
        airing_at = None
        if media.get("nextAiringEpisode"):
            next_ep = media["nextAiringEpisode"].get("episode")
            airing_at = media["nextAiringEpisode"].get("airingAt")

        record = {
            "id": aid,
            "title": media.get("title", {}).get("english") or media.get("title", {}).get("romaji"),
            "season": self.get_season_str(media),
            "current_ep": media.get("episodes") or 0,
            "next_ep": next_ep,
            "airing_at": airing_at,
            "status": media.get("status", "Unknown"),
            "score": media.get("averageScore"),
            "last_checked": datetime.utcnow().isoformat()
        }
        self.tracked[uid].append(record)
        self.save_data()

        embed = self.build_universal_embed(media, {"ep": record["current_ep"]})
        await interaction.followup.send(content="✅ Anime Added", embed=embed)

    @app_commands.command(name="epremove", description="Remove anime from your tracking list")
    @app_commands.describe(anime="Anime name")
    async def epremove(self, interaction: discord.Interaction, anime: str):
        if not await self.check_chat(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        uid = str(interaction.user.id)
        if uid not in self.tracked:
            await interaction.followup.send("No tracked anime.")
            return

        media = await self.fetch_anime_by_name(anime)
        if not media:
            # try match by title
            lower = anime.lower()
            for i, t in enumerate(self.tracked[uid]):
                if lower in t["title"].lower():
                    removed = self.tracked[uid].pop(i)
                    self.save_data()
                    await interaction.followup.send(f"❌ Removed\n📺 {removed['title']}")
                    return
            await interaction.followup.send("Not found in your list.")
            return

        aid = media["id"]
        for i, t in enumerate(self.tracked[uid]):
            if t.get("id") == aid:
                removed = self.tracked[uid].pop(i)
                self.save_data()
                await interaction.followup.send(f"❌ Removed\n📺 {removed['title']}")
                return
        await interaction.followup.send("Not tracking that one.")

    @app_commands.command(name="alertlist", description="Show your simple tracked anime list")
    async def alertlist(self, interaction: discord.Interaction):
        if not await self.check_chat(interaction):
            return
        await interaction.response.defer()

        uid = str(interaction.user.id)
        lst = self.tracked.get(uid, [])
        if not lst:
            await interaction.followup.send("No tracked anime. Use /epalert")
            return

        lines = [f"• {a['title']}" for a in lst]
        embed = discord.Embed(
            title="📺 Episode Alert List",
            description="\n".join(lines),
            color=COLOR_ANIME
        )
        embed.set_footer(text=f"Total Tracked: {len(lst)}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="myanime", description="Detailed dashboard of your tracked anime")
    async def myanime(self, interaction: discord.Interaction):
        if not await self.check_chat(interaction):
            return
        await interaction.response.defer()

        uid = str(interaction.user.id)
        lst = self.tracked.get(uid, [])
        if not lst:
            await interaction.followup.send("Nothing tracked.")
            return

        embed = discord.Embed(title="📚 My Anime Dashboard", color=COLOR_ANIME)
        for a in lst[:8]:  # limit
            season = f"\n🎭 {a['season']}" if a.get("season") else ""
            nextl = f"\n⏭️ Next: {a.get('next_ep')}" if a.get("next_ep") else ""
            embed.add_field(
                name=f"📺 {a['title']}",
                value=f"🎬 Current: {a.get('current_ep')}{season}{nextl}\n📡 {a.get('status')}",
                inline=False
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="nextrelease", description="Upcoming episodes countdown for tracked")
    async def nextrelease(self, interaction: discord.Interaction):
        if not await self.check_chat(interaction):
            return
        await interaction.response.defer()

        uid = str(interaction.user.id)
        lst = self.tracked.get(uid, [])
        if not lst:
            await interaction.followup.send("No tracked.")
            return

        embed = discord.Embed(title="⏰ Upcoming Episodes", color=COLOR_ANIME)
        now = datetime.utcnow().timestamp()
        for a in lst:
            if a.get("next_ep") and a.get("airing_at"):
                ts = a["airing_at"]
                delta = ts - now
                if delta > 0:
                    hours = int(delta // 3600)
                    days = hours // 24
                    time_str = f"In {days} Days" if days > 0 else f"In {hours} Hours"
                    season = a.get("season") or ""
                    embed.add_field(
                        name=f"📺 {a['title']}",
                        value=f"🎭 {season}\n🎬 Episode {a['next_ep']}\n🕒 {time_str}",
                        inline=False
                    )
        if not embed.fields:
            embed.description = "No upcoming soon."
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="animecalendar", description="Weekly airing schedule")
    async def animecalendar(self, interaction: discord.Interaction):
        if not await self.check_chat(interaction):
            return
        await interaction.response.defer()

        # simple: from tracked + airing
        uid = str(interaction.user.id)
        lst = self.tracked.get(uid, [])
        embed = discord.Embed(title="📅 Anime Calendar", color=COLOR_ANIME)
        days = {}
        for a in lst:
            if a.get("airing_at"):
                dt = datetime.fromtimestamp(a["airing_at"])
                dname = dt.strftime("%A")
                if dname not in days:
                    days[dname] = []
                days[dname].append(f"📺 {a['title']}")
        for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            if d in days:
                embed.add_field(name=d, value="\n".join(days[d]), inline=False)
        if not days:
            embed.description = "No schedule data."
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="weeklyanime", description="Releases in last 7 days from your list")
    async def weeklyanime(self, interaction: discord.Interaction):
        if not await self.check_chat(interaction):
            return
        await interaction.response.defer()

        uid = str(interaction.user.id)
        lst = self.tracked.get(uid, [])
        if not lst:
            await interaction.followup.send("No tracked.")
            return

        embed = discord.Embed(title="📅 Weekly Anime Report", color=COLOR_ANIME)
        count = 0
        for a in lst:
            # naive: if recently updated
            if a.get("current_ep"):
                embed.add_field(
                    name=f"📺 {a['title']}",
                    value=f"🎭 {a.get('season','')}\n🎬 Episode {a['current_ep']}",
                    inline=False
                )
                count += 1
        embed.set_footer(text=f"Total Released: {count}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="trendinganime", description="Current season top 10 trending anime")
    async def trendinganime(self, interaction: discord.Interaction):
        if not await self.check_chat(interaction):
            return
        await interaction.response.defer()

        media_list = await self.fetch_trending()
        if not media_list:
            await interaction.followup.send("Failed to fetch.")
            return

        embed = discord.Embed(title="🔥 Top 10 Trending Anime", color=COLOR_ANIME)
        for i, m in enumerate(media_list, 1):
            t = m.get("title", {}).get("english") or m.get("title", {}).get("romaji", "Unknown")
            score = m.get("averageScore", "N/A")
            embed.add_field(name=f"{i}. {t}", value=f"⭐ {score}/100", inline=False)
        await interaction.followup.send(embed=embed)

    # ── Background Tasks ─────────────────────
    @tasks.loop(minutes=15)
    async def check_episodes(self):
        await self.bot.wait_until_ready()
        if ANIME_UPDATES_CHANNEL_ID == 0:
            return
        updates_ch = self.bot.get_channel(ANIME_UPDATES_CHANNEL_ID)
        if not updates_ch:
            return

        now = datetime.utcnow().timestamp()
        changed = False
        for uid, animes in list(self.tracked.items()):
            for a in animes:
                media = await self.fetch_anime_by_id(a["id"])
                if not media:
                    continue

                cur_ep = media.get("episodes") or 0
                next_data = media.get("nextAiringEpisode") or {}
                next_ep = next_data.get("episode")
                airing_at = next_data.get("airingAt")

                old_next = a.get("next_ep")
                old_air = a.get("airing_at")

                # new episode released
                if next_ep and old_next and next_ep > old_next:
                    # episode dropped
                    embed = discord.Embed(
                        title="🚨 NEW EPISODE RELEASED",
                        color=0x00ff00
                    )
                    embed.add_field(name="📺", value=a["title"], inline=False)
                    embed.add_field(name="🎬", value=f"Episode {next_ep}", inline=True)
                    embed.add_field(name="📡", value="Available Now", inline=True)
                    await updates_ch.send(embed=embed)
                    a["current_ep"] = next_ep - 1 if next_ep else cur_ep
                    a["next_ep"] = next_ep
                    a["airing_at"] = airing_at
                    changed = True

                # delay detect
                if airing_at and old_air and airing_at > old_air + 3600:
                    embed = discord.Embed(title="⚠️ Episode Delayed", color=0xffaa00)
                    embed.add_field(name="📺", value=a["title"], inline=False)
                    embed.add_field(name="🎬", value=f"Episode {next_ep or old_next}", inline=True)
                    embed.add_field(name="Reason", value="Broadcast Schedule Change", inline=False)
                    await updates_ch.send(embed=embed)
                    a["airing_at"] = airing_at
                    changed = True

                # finale
                if media.get("status") == "FINISHED" and (cur_ep or 0) >= (a.get("current_ep") or 0):
                    if a.get("status") != "FINISHED":
                        embed = discord.Embed(title="🏁 Season Finale", color=0x9933ff)
                        embed.add_field(name="📺", value=a["title"], inline=False)
                        embed.add_field(name="🎬", value=f"Episode {cur_ep}", inline=True)
                        embed.add_field(name="Status", value="Season Completed", inline=False)
                        await updates_ch.send(embed=embed)
                        a["status"] = "FINISHED"
                        changed = True

                # update local
                a["current_ep"] = cur_ep
                a["status"] = media.get("status", a["status"])
                if next_ep:
                    a["next_ep"] = next_ep
                if airing_at:
                    a["airing_at"] = airing_at

        if changed:
            self.save_data()

    @tasks.loop(hours=6)
    async def check_new_seasons(self):
        await self.bot.wait_until_ready()
        if ANIME_UPDATES_CHANNEL_ID == 0:
            return
        updates_ch = self.bot.get_channel(ANIME_UPDATES_CHANNEL_ID)
        if not updates_ch:
            return
        # simple: re-search tracked and see season change
        for uid, animes in list(self.tracked.items()):
            for a in animes:
                media = await self.fetch_anime_by_id(a["id"])
                if not media:
                    continue
                new_season = self.get_season_str(media)
                if new_season and new_season != a.get("season"):
                    embed = discord.Embed(title="🎉 New Season Announced", color=0x00aaff)
                    embed.add_field(name="📺", value=a["title"], inline=False)
                    embed.add_field(name="🎭", value=new_season, inline=True)
                    embed.add_field(name="Status", value="Officially Confirmed", inline=False)
                    await updates_ch.send(embed=embed)
                    a["season"] = new_season
                    self.save_data()

    @tasks.loop(hours=24)
    async def weekly_report(self):
        await self.bot.wait_until_ready()
        if ANIME_UPDATES_CHANNEL_ID == 0:
            return
        updates_ch = self.bot.get_channel(ANIME_UPDATES_CHANNEL_ID)
        if not updates_ch:
            return
        now = datetime.utcnow()
        if now.weekday() != 4:  # Friday = 4
            return
        if self.last_weekly and (now - self.last_weekly).days < 6:
            return

        # build from all tracked recent eps
        embed = discord.Embed(title="📅 Weekly Anime Report", color=COLOR_ANIME)
        total = 0
        for uid, animes in list(self.tracked.items()):
            for a in animes:
                if a.get("current_ep"):
                    season = f"\n🎭 {a.get('season')}" if a.get("season") else ""
                    embed.add_field(
                        name=f"📺 {a['title']}",
                        value=f"🎬 Episode {a['current_ep']}{season}",
                        inline=False
                    )
                    total += 1
        embed.set_footer(text=f"Total Released: {total}")
        await updates_ch.send(embed=embed)
        self.last_weekly = now
        self.save_data()


async def setup(bot):
    await bot.add_cog(Alerts(bot))
