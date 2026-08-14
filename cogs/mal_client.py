# ============================================
#   Sansa Bot — Official MyAnimeList API v2
#   Docs: https://myanimelist.net/apiconfig/references/api/v2
# ============================================

from __future__ import annotations

import aiohttp
import logging
import random
from typing import Optional
from config import MAL_CLIENT_ID

log = logging.getLogger("SansaBot.MAL")

BASE = "https://api.myanimelist.net/v2"

ANIME_FIELDS = (
    "id,title,main_picture,alternative_titles,start_date,synopsis,mean,"
    "num_episodes,status,genres,start_season,media_type,average_episode_duration"
)

MANGA_FIELDS = (
    "id,title,main_picture,alternative_titles,start_date,synopsis,mean,"
    "num_chapters,num_volumes,status,genres,authors{first_name,last_name}"
)

CHAR_FIELDS = "id,first_name,last_name,alternative_name,main_picture,biography,animeography,mangaography"


def mal_configured() -> bool:
    return bool(MAL_CLIENT_ID and MAL_CLIENT_ID not in ("", "YOUR_MAL_CLIENT_ID_HERE", "0"))


def _headers() -> dict:
    return {
        "X-MAL-CLIENT-ID": MAL_CLIENT_ID,
        "User-Agent": "SansaBot/1.0",
        "Accept": "application/json",
    }


async def mal_get(path: str, params: Optional[dict] = None):
    """GET official MAL API. Returns JSON dict or None."""
    if not mal_configured():
        return None
    url = f"{BASE}/{path.lstrip('/')}"
    try:
        timeout = aiohttp.ClientTimeout(total=12)
        async with aiohttp.ClientSession(timeout=timeout, headers=_headers()) as session:
            async with session.get(url, params=params or {}) as resp:
                if resp.status == 200:
                    return await resp.json()
                text = await resp.text()
                log.warning(f"MAL {resp.status} {path}: {text[:180]}")
    except Exception as e:
        log.warning(f"MAL request failed {path}: {e}")
    return None


# ── Normalize → common shape used by cogs ──

def normalize_anime(node: dict) -> dict:
    """MAL node → Jikan-like shape (cogs check mal_id)."""
    if not node:
        return {}
    alt = node.get("alternative_titles") or {}
    en = alt.get("en") or ""
    pic = node.get("main_picture") or {}
    image = pic.get("large") or pic.get("medium") or ""
    genres = [{"name": g.get("name", "")} for g in (node.get("genres") or []) if g.get("name")]
    start = node.get("start_date") or ""
    year = int(start[:4]) if len(start) >= 4 and start[:4].isdigit() else None
    season = node.get("start_season") or {}
    if year is None and season.get("year"):
        year = season.get("year")
    mean = node.get("mean")
    status_raw = (node.get("status") or "").replace("_", " ").title()
    # duration: MAL seconds → minutes for watchtime
    dur_sec = node.get("average_episode_duration")
    dur_min = int(dur_sec / 60) if isinstance(dur_sec, (int, float)) and dur_sec > 0 else None
    return {
        "mal_id": node.get("id"),
        "title": node.get("title") or "Unknown",
        "title_english": en or None,
        "synopsis": node.get("synopsis") or "No description available.",
        "score": mean if mean is not None else "N/A",
        "episodes": node.get("num_episodes") if node.get("num_episodes") is not None else "N/A",
        "year": year if year is not None else "N/A",
        "genres": genres,
        "status": status_raw or "Unknown",
        "images": {"jpg": {"large_image_url": image, "image_url": image}},
        "duration": dur_min,
        "media_type": node.get("media_type"),
        "start_season": season,
        "_source": "mal",
    }


def normalize_manga(node: dict) -> dict:
    """MAL node → embed-friendly + AniList-compat keys for auto.py."""
    if not node:
        return {}
    alt = node.get("alternative_titles") or {}
    en = alt.get("en") or ""
    pic = node.get("main_picture") or {}
    image = pic.get("large") or pic.get("medium") or ""
    genre_names = [g.get("name", "") for g in (node.get("genres") or []) if g.get("name")]
    start = node.get("start_date") or ""
    year = int(start[:4]) if len(start) >= 4 and start[:4].isdigit() else None
    mean = node.get("mean")
    status_raw = (node.get("status") or "").replace("_", " ").title()
    authors = []
    for a in node.get("authors") or []:
        n = a.get("node") or {}
        name = f"{n.get('first_name', '')} {n.get('last_name', '')}".strip()
        if name:
            authors.append(name)
    title = node.get("title") or "Unknown"
    return {
        "mal_id": node.get("id"),
        "title": {"romaji": title, "english": en or title},
        "description": node.get("synopsis") or "No description available.",
        "synopsis": node.get("synopsis") or "No description available.",
        "averageScore": mean if mean is not None else "N/A",
        "score": mean if mean is not None else "N/A",
        "chapters": node.get("num_chapters") if node.get("num_chapters") is not None else "N/A",
        "volumes": node.get("num_volumes") if node.get("num_volumes") is not None else "N/A",
        "startDate": {"year": year},
        "year": year if year is not None else "N/A",
        "genres": genre_names,
        "status": status_raw or "Unknown",
        "author": authors[0] if authors else "Unknown",
        "coverImage": {"extraLarge": image, "large": image},
        "images": {"jpg": {"large_image_url": image, "image_url": image}},
        "siteUrl": f"https://myanimelist.net/manga/{node.get('id')}",
        "site_url": f"https://myanimelist.net/manga/{node.get('id')}",
        "_source": "mal",
    }


def _nodes_from_list(data: dict) -> list:
    if not data:
        return []
    out = []
    for item in data.get("data") or []:
        node = item.get("node") if isinstance(item, dict) and "node" in item else item
        if node:
            out.append(node)
    return out


# ── Public fetch helpers ───────────────────

async def search_anime(title: str, limit: int = 1) -> list:
    data = await mal_get("anime", {
        "q": title[:64],
        "limit": min(limit, 20),
        "fields": ANIME_FIELDS,
    })
    return [normalize_anime(n) for n in _nodes_from_list(data)]


async def get_anime(anime_id: int) -> Optional[dict]:
    data = await mal_get(f"anime/{anime_id}", {"fields": ANIME_FIELDS})
    return normalize_anime(data) if data else None


async def random_anime() -> Optional[dict]:
    """Random via ranking offset (official API has no /random)."""
    offset = random.randint(0, 400)
    data = await mal_get("anime/ranking", {
        "ranking_type": "bypopularity",
        "limit": 1,
        "offset": offset,
        "fields": ANIME_FIELDS,
    })
    nodes = _nodes_from_list(data)
    if nodes:
        return normalize_anime(nodes[0])
    # last resort: top page pick
    data = await mal_get("anime/ranking", {
        "ranking_type": "all",
        "limit": 20,
        "fields": ANIME_FIELDS,
    })
    nodes = _nodes_from_list(data)
    if nodes:
        return normalize_anime(random.choice(nodes))
    return None


async def top_anime(limit: int = 10) -> list:
    data = await mal_get("anime/ranking", {
        "ranking_type": "all",
        "limit": min(limit, 50),
        "fields": ANIME_FIELDS,
    })
    return [normalize_anime(n) for n in _nodes_from_list(data)]


async def season_anime(year: int, season: str, limit: int = 10) -> list:
    """season: winter|spring|summer|fall"""
    data = await mal_get(f"anime/season/{year}/{season.lower()}", {
        "limit": min(limit, 50),
        "fields": ANIME_FIELDS,
        "sort": "anime_num_list_users",
    })
    return [normalize_anime(n) for n in _nodes_from_list(data)]


async def search_manga(title: str, limit: int = 1) -> list:
    data = await mal_get("manga", {
        "q": title[:64],
        "limit": min(limit, 20),
        "fields": MANGA_FIELDS,
    })
    return [normalize_manga(n) for n in _nodes_from_list(data)]


async def random_manga() -> Optional[dict]:
    offset = random.randint(0, 400)
    data = await mal_get("manga/ranking", {
        "ranking_type": "bypopularity",
        "limit": 1,
        "offset": offset,
        "fields": MANGA_FIELDS,
    })
    nodes = _nodes_from_list(data)
    if nodes:
        return normalize_manga(nodes[0])
    data = await mal_get("manga/ranking", {
        "ranking_type": "all",
        "limit": 20,
        "fields": MANGA_FIELDS,
    })
    nodes = _nodes_from_list(data)
    if nodes:
        return normalize_manga(random.choice(nodes))
    return None


async def search_character(name: str, limit: int = 1) -> list:
    """Character search — not in public MAL v2; returns []. Use Jikan fallback."""
    return []
