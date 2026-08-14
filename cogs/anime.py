# ============================================
#   Sansa Bot — Anime Cog (MyAnimeList only)
#   Commands: /anime, /character, /top, /season, /watchtime, /watchlink
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import difflib
from datetime import datetime, timezone
from urllib.parse import quote_plus
from config import (
    CHAT_CHANNEL_ID, COLOR_ANIME, COLOR_ERROR
)
from cogs import mal_client

try:
    import cloudscraper
    from bs4 import BeautifulSoup
except ImportError:
    cloudscraper = None
    BeautifulSoup = None

log = logging.getLogger("SansaBot.Anime")


class WatchtimeView(discord.ui.View):
    def __init__(self, results, author_id, cog):
        super().__init__(timeout=30.0)
        self.results = results
        self.author_id = author_id
        self.cog = cog
        self.message = None

        options = []
        for i, m in enumerate(results):
            title = m.get("title", {}).get("english") or m.get("title", {}).get("romaji", "Unknown")
            season = m.get("season") or ""
            year = m.get("seasonYear") or ""
            fmt = m.get("format") or ""
            label = title
            if season and year:
                label += f" {season} {year}"
            elif fmt:
                label += f" ({fmt})"
            if len(label) > 100:
                label = label[:97] + "..."
            options.append(discord.SelectOption(label=label, value=str(i)))

        options.append(discord.SelectOption(label="🔥 All Seasons Combined", value="COMBINED"))

        select = discord.ui.Select(
            placeholder="Choose an option...",
            options=options[:25],
            min_values=1,
            max_values=1
        )
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Only the person who used the command can select.", ephemeral=True
            )
            return

        value = interaction.data.get("values", [None])[0]
        if value == "COMBINED":
            await self.show_combined(interaction)
        else:
            try:
                idx = int(value)
                media = self.results[idx]
                await self.show_single(interaction, media)
            except (ValueError, IndexError):
                await interaction.response.send_message("❌ Invalid selection.", ephemeral=True)
                return

        self.stop()

    async def show_single(self, interaction, media):
        title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji", "Unknown")
        episodes = media.get("episodes") or 0
        per_ep = self.cog.parse_duration(media.get("duration"))

        if episodes <= 0:
            await interaction.response.send_message(
                "❌ Episode count not available for this title.", ephemeral=True
            )
            return

        total_min = episodes * per_ep
        total_h = round(total_min / 60, 1)
        total_d = round(total_h / 24, 1)

        embed = discord.Embed(title=f"📺 {title}", color=COLOR_ANIME)
        embed.add_field(name="🎬 Episodes", value=str(episodes), inline=True)
        embed.add_field(name="⏱️ Per Episode", value=f"{per_ep} min", inline=True)
        embed.add_field(name="\u200b", value="─────────────────", inline=False)
        embed.add_field(name="⏱️ Total", value=f"{total_h} hours", inline=False)
        embed.add_field(name="📅 That's", value=f"{total_d} days of your life! 😭", inline=False)
        embed.set_footer(text="Sansa Bot 🌸 • MyAnimeList")

        await interaction.response.edit_message(content=None, embed=embed, view=None)

    async def show_combined(self, interaction):
        lines = []
        grand_total_min = 0

        base_title = (
            self.results[0].get("title", {}).get("english")
            or self.results[0].get("title", {}).get("romaji", "Series")
        )

        for m in self.results:
            title = m.get("title", {}).get("english") or m.get("title", {}).get("romaji", "Unknown")
            ep = m.get("episodes") or 0
            dur = self.cog.parse_duration(m.get("duration"))
            if ep <= 0:
                continue
            h = round(ep * dur / 60, 1)
            lines.append(f"{title}      →  {ep} ep × {dur} min =  {h} hrs")
            grand_total_min += ep * dur

        if not lines:
            await interaction.response.send_message("❌ No valid data for combined.", ephemeral=True)
            return

        total_h = round(grand_total_min / 60, 1)
        total_d = round(total_h / 24, 1)

        breakdown = "\n".join(lines)
        embed = discord.Embed(title=f"📺 {base_title} — Complete Series", color=COLOR_ANIME)
        embed.add_field(name="Breakdown", value=breakdown[:1024], inline=False)
        embed.add_field(name="\u200b", value="─────────────────────────────────", inline=False)
        embed.add_field(name="⏱️ Total", value=f"{total_h} hours", inline=False)
        embed.add_field(name="📅 That's", value=f"{total_d} days of your life! 😭", inline=False)
        embed.set_footer(text="Sansa Bot 🌸 • MyAnimeList")

        await interaction.response.edit_message(content=None, embed=embed, view=None)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(
                    content="⏰ Time's up!\nMenu expired. আবার /watchtime দাও।", view=None
                )
            except discord.HTTPException:
                pass


class Anime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Anime Cog loaded (MyAnimeList only)")

    async def check_channel(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != CHAT_CHANNEL_ID:
            embed = discord.Embed(
                description=f"❌ This command only works in <#{CHAT_CHANNEL_ID}>!",
                color=COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    def parse_duration(self, dur):
        if not dur:
            return 24
        if isinstance(dur, (int, float)):
            val = int(dur)
            return val if 1 <= val <= 180 else 24
        try:
            nums = "".join(c for c in str(dur) if c.isdigit())
            val = int(nums) if nums else 24
            return val if 1 <= val <= 180 else 24
        except (ValueError, TypeError):
            return 24

    def _anime_embed(self, anime: dict, random_mode: bool = False) -> discord.Embed:
        desc = anime.get("synopsis") or "No description available."
        if len(desc) > 350:
            desc = desc[:350] + "..."
        title_en = anime.get("title_english") or anime.get("title") or "Unknown"
        title_jp = anime.get("title") or ""
        genres = ", ".join(
            [g.get("name", "") if isinstance(g, dict) else str(g) for g in (anime.get("genres") or [])][:4]
        ) or "Unknown"
        image_url = (
            (anime.get("images") or {}).get("jpg", {}).get("large_image_url")
            or (anime.get("images") or {}).get("jpg", {}).get("image_url")
        )
        site_url = anime.get("site_url") or (
            f"https://myanimelist.net/anime/{anime.get('mal_id')}" if anime.get("mal_id") else None
        )
        prefix = "🎲 Random Anime — " if random_mode else "🎌 "
        embed = discord.Embed(
            title=f"{prefix}{title_en}"[:256],
            description=f"*{title_jp}*\n\n{desc}",
            color=COLOR_ANIME,
            url=site_url,
        )
        embed.add_field(name="⭐ Score", value=f"{anime.get('score', 'N/A')}/10", inline=True)
        embed.add_field(name="📺 Episodes", value=str(anime.get("episodes", "N/A")), inline=True)
        if not random_mode:
            embed.add_field(name="📊 Status", value=str(anime.get("status", "Unknown")), inline=True)
        embed.add_field(name="📅 Year", value=str(anime.get("year", "N/A")), inline=True)
        embed.add_field(name="🎭 Genres", value=genres, inline=False)
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(text="Sansa Bot 🌸 • MyAnimeList")
        return embed

    # ── /anime ─────────────────────────────
    @app_commands.command(name="anime", description="🎌 Get details for a random or specific anime (MyAnimeList)")
    @app_commands.describe(title="Anime title (leave empty for random)")
    async def anime(self, interaction: discord.Interaction, title: str = None):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        if title:
            hits = await mal_client.search_anime(title, limit=1)
            if not hits:
                embed = discord.Embed(
                    description=f"❌ No anime found with the name **{title}**!",
                    color=COLOR_ERROR,
                )
                await interaction.followup.send(embed=embed)
                return
            await interaction.followup.send(embed=self._anime_embed(hits[0], random_mode=False))
        else:
            anime = await mal_client.random_anime()
            if not anime:
                embed = discord.Embed(
                    description="❌ Failed to fetch anime from MyAnimeList. Try again.",
                    color=COLOR_ERROR,
                )
                await interaction.followup.send(embed=embed)
                return
            await interaction.followup.send(embed=self._anime_embed(anime, random_mode=True))

    # ── /character ─────────────────────────
    @app_commands.command(name="character", description="👤 Get details for an anime character (MyAnimeList)")
    @app_commands.describe(name="Character name")
    async def character(self, interaction: discord.Interaction, name: str):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        chars = await mal_client.search_character(name, limit=1)
        if not chars:
            embed = discord.Embed(
                description=f"❌ No character found with the name **{name}**!",
                color=COLOR_ERROR,
            )
            await interaction.followup.send(embed=embed)
            return

        char = chars[0]
        desc = char.get("about") or "No description available."
        if len(desc) > 350:
            desc = desc[:350] + "..."
        image_url = (char.get("images") or {}).get("jpg", {}).get("image_url")
        embed = discord.Embed(
            title=f"👤 {char.get('name', 'Unknown')}",
            description=desc,
            color=COLOR_ANIME,
            url=char.get("site_url") or None,
        )
        embed.add_field(name="📺 From", value=str(char.get("anime_from", "Unknown")), inline=True)
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(text="Sansa Bot 🌸 • MyAnimeList")
        await interaction.followup.send(embed=embed)

    # ── /top ───────────────────────────────
    @app_commands.command(name="top", description="🏆 Show Top 10 Anime (MyAnimeList)")
    async def top(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        media_list = await mal_client.top_anime(10)
        if not media_list:
            embed = discord.Embed(description="❌ Failed to fetch top anime!", color=COLOR_ERROR)
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(title="🏆 Top 10 Anime", color=COLOR_ANIME)
        image_url = None
        for i, anime in enumerate(media_list[:10], 1):
            title_en = anime.get("title_english") or anime.get("title", "Unknown")
            score = anime.get("score", "N/A")
            genres = ", ".join(
                [g.get("name", "") if isinstance(g, dict) else str(g) for g in (anime.get("genres") or [])][:2]
            )
            embed.add_field(
                name=f"{i}. {title_en}",
                value=f"⭐ {score}/10 | 🎭 {genres or '—'}",
                inline=False,
            )
            if i == 1:
                image_url = (anime.get("images") or {}).get("jpg", {}).get("large_image_url")
        if image_url:
            embed.set_thumbnail(url=image_url)
        embed.set_footer(text="Sansa Bot 🌸 • MyAnimeList")
        await interaction.followup.send(embed=embed)

    # ── /season ────────────────────────────
    @app_commands.command(name="season", description="📅 Show current season anime list (MyAnimeList)")
    async def season(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        now = datetime.now(timezone.utc)
        month, year = now.month, now.year
        season_map = {
            (12, 1, 2): "WINTER",
            (3, 4, 5): "SPRING",
            (6, 7, 8): "SUMMER",
            (9, 10, 11): "FALL",
        }
        current_season = "WINTER"
        for months, season in season_map.items():
            if month in months:
                current_season = season
                break

        mal_year = year + 1 if (current_season == "WINTER" and month == 12) else year
        media_list = await mal_client.season_anime(mal_year, current_season, 10)
        if not media_list:
            embed = discord.Embed(description="❌ Failed to fetch season anime!", color=COLOR_ERROR)
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"📅 {current_season.title()} {mal_year} Anime",
            color=COLOR_ANIME,
        )
        for i, anime in enumerate(media_list[:10], 1):
            title_en = anime.get("title_english") or anime.get("title", "Unknown")
            score = anime.get("score", "N/A")
            embed.add_field(name=f"{i}. {title_en}", value=f"⭐ {score}/10", inline=True)

        thumb = (media_list[0].get("images") or {}).get("jpg", {}).get("large_image_url")
        if thumb:
            embed.set_thumbnail(url=thumb)
        embed.set_footer(text="Sansa Bot 🌸 • MyAnimeList")
        await interaction.followup.send(embed=embed)

    # ── /watchtime ─────────────────────────
    @app_commands.command(name="watchtime", description="Calculate total watch time for an anime (MyAnimeList)")
    @app_commands.describe(title="Anime title")
    async def watchtime(self, interaction: discord.Interaction, title: str):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        hits = await mal_client.search_anime(title, limit=8)
        results = [mal_client.to_watchtime_item(a) for a in hits]

        if not results:
            embed = discord.Embed(
                description=f"❌ No anime found with **{title}**!",
                color=COLOR_ERROR,
            )
            await interaction.followup.send(embed=embed)
            return

        if len(results) == 1:
            await self.send_watchtime_single(interaction, results[0])
            return

        view = WatchtimeView(results, interaction.user.id, self)
        msg = await interaction.followup.send(
            f"🔍 Multiple results for **{title}**. Select one:",
            view=view,
        )
        view.message = msg

    async def send_watchtime_single(self, interaction, media):
        title = media.get("title", {}).get("english") or media.get("title", {}).get("romaji", "Unknown")
        episodes = media.get("episodes") or 0
        per_ep = self.parse_duration(media.get("duration"))

        if episodes <= 0:
            await interaction.followup.send("❌ Episode count not available.")
            return

        total_min = episodes * per_ep
        total_h = round(total_min / 60, 1)
        total_d = round(total_h / 24, 1)

        embed = discord.Embed(title=f"📺 {title}", color=COLOR_ANIME)
        embed.add_field(name="🎬 Episodes", value=str(episodes), inline=True)
        embed.add_field(name="⏱️ Per Episode", value=f"{per_ep} min", inline=True)
        embed.add_field(name="\u200b", value="─────────────────", inline=False)
        embed.add_field(name="⏱️ Total", value=f"{total_h} hours", inline=False)
        embed.add_field(name="📅 That's", value=f"{total_d} days of your life! 😭", inline=False)
        embed.set_footer(text="Sansa Bot 🌸 • MyAnimeList")
        await interaction.followup.send(embed=embed)

    # ── /watchlink ─────────────────────────
    @app_commands.command(name="watchlink", description="🔗 Get direct watch page links (enma + anikoto)")
    @app_commands.describe(title="Anime title")
    async def watchlink(self, interaction: discord.Interaction, title: str):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        if not cloudscraper or not BeautifulSoup:
            sites = {
                "Enma": f"https://www.enma.lol/search?keyword={quote_plus(title)}",
                "Anikoto": f"https://anikototv.to/filter?keyword={quote_plus(title)}",
            }
            embed = discord.Embed(title=f"🔗 Watch Links — {title}", color=COLOR_ANIME)
            for name, url in sites.items():
                embed.add_field(name=name, value=f"[Search]({url})", inline=False)
            await interaction.followup.send(embed=embed)
            return

        sites = [
            {"name": "Enma", "searches": ["https://www.enma.lol/search?keyword={q}"], "domain": "enma.lol"},
            {"name": "Anikoto", "searches": ["https://anikototv.to/filter?keyword={q}"], "domain": "anikototv.to"},
        ]

        embed = discord.Embed(
            title=f"🔗 Watch Links — {title}",
            description="Direct links from working sites (search fallback if needed)",
            color=COLOR_ANIME,
        )

        async def find_link(site):
            q = quote_plus(title)
            loop = asyncio.get_running_loop()

            def _scrape_one(url):
                try:
                    scraper = cloudscraper.create_scraper(
                        browser={"browser": "chrome", "platform": "windows", "mobile": False}
                    )
                    resp = scraper.get(url, timeout=8)
                    if resp.status_code != 200:
                        return None
                    soup = BeautifulSoup(resp.text, "lxml")
                    return self._pick_best_match(soup, title, site["domain"])
                except Exception as e:
                    log.warning(f"watchlink {site['name']} {url} err: {e}")
                    return None

            for tmpl in site.get("searches", []):
                search_url = tmpl.format(q=q)
                link = await loop.run_in_executor(None, _scrape_one, search_url)
                if link:
                    return site["name"], link
            return site["name"], site["searches"][0].format(q=q)

        tasks = [find_link(s) for s in sites]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in results:
            if isinstance(item, Exception):
                continue
            name, url = item
            if url.startswith("http"):
                if "/search" in url or "/filter" in url:
                    val = f"[🔍 Search]({url})"
                else:
                    val = f"[▶️ Watch]({url})"
            else:
                val = url
            embed.add_field(name=name, value=val, inline=False)

        await interaction.followup.send(embed=embed)

    def _pick_best_match(self, soup, title: str, domain: str):
        if not soup:
            return None
        title_l = title.lower().strip()
        key_words = [w for w in title_l.split() if len(w) >= 3]
        candidates = []
        good_paths = ("/watch/", "/anime/", "/play/", "/series/", "/stream/", "/detail/", "/title/", "/movie/")

        for a in soup.find_all("a", href=True)[:80]:
            href = a["href"].strip()
            if not href or href == "#" or "javascript" in href.lower():
                continue
            if href.startswith("/"):
                href = f"https://{domain}{href}"
            if domain not in href:
                continue
            bad = ["/search", "/filter", "/home", "/login", "/register", "/genre", "/type", "/tag", "/category"]
            if any(b in href for b in bad):
                continue
            txt = (a.get_text() or "").strip()
            if not txt:
                txt = a.get("title", "") or a.get("aria-label", "") or a.get("data-title", "")
            txt_l = txt.lower()
            slug = href.split("/")[-1].lower().replace("-", " ").replace("_", " ")
            score = difflib.SequenceMatcher(None, title_l, txt_l).ratio()
            score += difflib.SequenceMatcher(None, title_l, slug).ratio() * 0.6
            if any(kw in txt_l or kw in slug for kw in key_words):
                score += 0.3
            if any(p in href for p in good_paths):
                score += 0.15
            if score >= 0.22:
                candidates.append((score, href, (txt or slug)[:70]))

        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
        return None


async def setup(bot):
    await bot.add_cog(Anime(bot))
