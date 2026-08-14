# ============================================
#   Sansa Bot — MyAnimeList only
#   Official API v2 + Jikan v4 fallback (MAL data)
#   No AniList.
# ============================================

from __future__ import annotations

import aiohttp
import logging
import random
from typing import Optional
from urllib.parse import quote
from config import MAL_CLIENT_ID

log = logging.getLogger("SansaBot.MAL")

BASE = "https://api.myanimelist.net/v2"
JIKAN = "https://api.jikan.moe/v4"

ANIME_FIELDS = (
    "id,title,main_picture,alternative_titles,start_date,synopsis,mean,"
    "num_episodes,status,genres,start_season,media_type,average_episode_duration"
)

MANGA_FIELDS = (
    "id,title,main_picture,alternative_titles,start_date,synopsis,mean,"
    "num_chapters,num_volumes,status,genres,authors{first_name,last_name}"
)


def mal_configured() -> bool:
    return bool(MAL_CLIENT_ID and MAL_CLIENT_ID not in ("", "YOUR_MAL_CLIENT_ID_HERE", "0"))


def _mal_headers() -> dict:
    return {
        "X-MAL-CLIENT-ID": MAL_CLIENT_ID,
        "User-Agent": "SansaBot/1.0",
        "Accept": "application/json",
    }


def _ua_headers() -> dict:
    return {"User-Agent": "SansaBot/1.0", "Accept": "application/json"}


async def mal_get(path: str, params: Optional[dict] = None):
    if not mal_configured():
        return None
    url = f"{BASE}/{path.lstrip('/')}"
    try:
        timeout = aiohttp.ClientTimeout(total=12)
        async with aiohttp.ClientSession(timeout=timeout, headers=_mal_headers()) as session:
            async with session.get(url, params=params or {}) as resp:
                if resp.status == 200:
                    return await resp.json()
                text = await resp.text()
                log.warning(f"MAL {resp.status} {path}: {text[:180]}")
    except Exception as e:
        log.warning(f"MAL request failed {path}: {e}")
    return None


async def jikan_get(endpoint: str):
    """Jikan = unofficial MyAnimeList API (same MAL ids/links)."""
    url = f"{JIKAN}/{endpoint.lstrip('/')}"
    try:
        timeout = aiohttp.ClientTimeout(total=12)
        async with aiohttp.ClientSession(timeout=timeout, headers=_ua_headers()) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                log.warning(f"Jikan {resp.status} {endpoint}")
    except Exception as e:
        log.warning(f"Jikan failed {endpoint}: {e}")
    return None


# ── Normalize → unified MAL-shaped dict ────

def normalize_anime(node: dict) -> dict:
    """Official MAL node → unified shape."""
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
    dur_sec = node.get("average_episode_duration")
    dur_min = int(dur_sec / 60) if isinstance(dur_sec, (int, float)) and dur_sec > 0 else 24
    title = node.get("title") or "Unknown"
    return {
        "mal_id": node.get("id"),
        "title": title,
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
        "site_url": f"https://myanimelist.net/anime/{node.get('id')}",
        "_source": "mal",
    }


def normalize_jikan_anime(a: dict) -> dict:
    """Jikan anime object → same unified shape."""
    if not a:
        return {}
    mal_id = a.get("mal_id")
    year = a.get("year")
    if year is None:
        aired = (a.get("aired") or {}).get("from") or ""
        if len(aired) >= 4 and aired[:4].isdigit():
            year = int(aired[:4])
    season = a.get("season")
    season_year = a.get("year")
    return {
        "mal_id": mal_id,
        "title": a.get("title") or "Unknown",
        "title_english": a.get("title_english"),
        "synopsis": a.get("synopsis") or "No description available.",
        "score": a.get("score") if a.get("score") is not None else "N/A",
        "episodes": a.get("episodes") if a.get("episodes") is not None else "N/A",
        "year": year if year is not None else "N/A",
        "genres": a.get("genres") or [],
        "status": a.get("status") or "Unknown",
        "images": a.get("images") or {},
        "duration": a.get("duration"),  # e.g. "24 min per ep"
        "media_type": a.get("type"),
        "start_season": {"season": season, "year": season_year} if season else {},
        "site_url": f"https://myanimelist.net/anime/{mal_id}" if mal_id else "",
        "_source": "jikan",
    }


def normalize_manga(node: dict) -> dict:
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
        "title_raw": title,
        "title_english": en or None,
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


def normalize_jikan_manga(m: dict) -> dict:
    if not m:
        return {}
    mal_id = m.get("mal_id")
    title = m.get("title") or "Unknown"
    en = m.get("title_english")
    img = (m.get("images") or {}).get("jpg", {})
    image = img.get("large_image_url") or img.get("image_url") or ""
    year = None
    published = (m.get("published") or {}).get("from") or ""
    if len(published) >= 4 and published[:4].isdigit():
        year = int(published[:4])
    authors = []
    for a in m.get("authors") or []:
        if a.get("name"):
            authors.append(a["name"])
    genres = [g.get("name", "") for g in (m.get("genres") or []) if g.get("name")]
    return {
        "mal_id": mal_id,
        "title": {"romaji": title, "english": en or title},
        "title_raw": title,
        "title_english": en,
        "description": m.get("synopsis") or "No description available.",
        "synopsis": m.get("synopsis") or "No description available.",
        "averageScore": m.get("score") if m.get("score") is not None else "N/A",
        "score": m.get("score") if m.get("score") is not None else "N/A",
        "chapters": m.get("chapters") if m.get("chapters") is not None else "N/A",
        "volumes": m.get("volumes") if m.get("volumes") is not None else "N/A",
        "startDate": {"year": year},
        "year": year if year is not None else "N/A",
        "genres": genres,
        "status": m.get("status") or "Unknown",
        "author": authors[0] if authors else "Unknown",
        "coverImage": {"extraLarge": image, "large": image},
        "images": m.get("images") or {},
        "siteUrl": f"https://myanimelist.net/manga/{mal_id}" if mal_id else "",
        "site_url": f"https://myanimelist.net/manga/{mal_id}" if mal_id else "",
        "_source": "jikan",
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


def to_watchtime_item(anime: dict) -> dict:
    """Unified anime → watchtime dropdown item."""
    en = anime.get("title_english")
    jp = anime.get("title") or "Unknown"
    season_info = anime.get("start_season") or {}
    season = (season_info.get("season") or "").upper() if isinstance(season_info, dict) else ""
    year = season_info.get("year") if isinstance(season_info, dict) else None
    if year is None and anime.get("year") not in (None, "N/A"):
        year = anime.get("year")
    eps = anime.get("episodes")
    try:
        eps = int(eps) if eps not in (None, "N/A") else 0
    except (TypeError, ValueError):
        eps = 0
    dur = anime.get("duration")
    if isinstance(dur, str):
        nums = "".join(c for c in dur if c.isdigit())
        dur = int(nums) if nums else 24
        if dur > 120:
            dur = 24
    elif not isinstance(dur, (int, float)) or dur <= 0:
        dur = 24
    else:
        dur = int(dur)
    return {
        "title": {"english": en or jp, "romaji": jp},
        "episodes": eps,
        "duration": dur,
        "season": season,
        "seasonYear": year,
        "format": anime.get("media_type") or "",
        "mal_id": anime.get("mal_id"),
    }


# ── Public API (MAL first, Jikan fallback) ─

async def search_anime(title: str, limit: int = 1) -> list:
    data = await mal_get("anime", {
        "q": title[:64],
        "limit": min(limit, 20),
        "fields": ANIME_FIELDS,
    })
    nodes = _nodes_from_list(data)
    if nodes:
        return [normalize_anime(n) for n in nodes]
    j = await jikan_get(f"anime?q={quote(title)}&limit={min(limit, 20)}")
    if j and j.get("data"):
        return [normalize_jikan_anime(a) for a in j["data"]]
    return []


async def random_anime() -> Optional[dict]:
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
    j = await jikan_get("random/anime")
    if j and j.get("data"):
        return normalize_jikan_anime(j["data"])
    return None


async def top_anime(limit: int = 10) -> list:
    data = await mal_get("anime/ranking", {
        "ranking_type": "all",
        "limit": min(limit, 50),
        "fields": ANIME_FIELDS,
    })
    nodes = _nodes_from_list(data)
    if nodes:
        return [normalize_anime(n) for n in nodes]
    j = await jikan_get(f"top/anime?limit={min(limit, 25)}")
    if j and j.get("data"):
        return [normalize_jikan_anime(a) for a in j["data"]]
    return []


async def season_anime(year: int, season: str, limit: int = 10) -> list:
    data = await mal_get(f"anime/season/{year}/{season.lower()}", {
        "limit": min(limit, 50),
        "fields": ANIME_FIELDS,
        "sort": "anime_num_list_users",
    })
    nodes = _nodes_from_list(data)
    if nodes:
        return [normalize_anime(n) for n in nodes]
    j = await jikan_get(f"seasons/now?limit={min(limit, 25)}")
    if j and j.get("data"):
        return [normalize_jikan_anime(a) for a in j["data"]]
    return []


async def search_manga(title: str, limit: int = 1) -> list:
    data = await mal_get("manga", {
        "q": title[:64],
        "limit": min(limit, 20),
        "fields": MANGA_FIELDS,
    })
    nodes = _nodes_from_list(data)
    if nodes:
        return [normalize_manga(n) for n in nodes]
    j = await jikan_get(f"manga?q={quote(title)}&limit={min(limit, 20)}")
    if j and j.get("data"):
        return [normalize_jikan_manga(m) for m in j["data"]]
    return []


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
    j = await jikan_get("random/manga")
    if j and j.get("data"):
        return normalize_jikan_manga(j["data"])
    # Jikan random manga sometimes 404 — try top page
    j = await jikan_get("top/manga?limit=25")
    if j and j.get("data"):
        return normalize_jikan_manga(random.choice(j["data"]))
    return None


async def search_character(name: str, limit: int = 1) -> list:
    """Characters via Jikan (MAL data). Official MAL v2 has no public char search."""
    j = await jikan_get(f"characters?q={quote(name)}&limit={min(limit, 10)}")
    if not j or not j.get("data"):
        return []
    out = []
    for c in j["data"]:
        mal_id = c.get("mal_id")
        anime_from = "Unknown"
        # full character for anime list needs extra call — use name only if thin
        out.append({
            "mal_id": mal_id,
            "name": c.get("name") or "Unknown",
            "about": c.get("about") or "No description available.",
            "images": c.get("images") or {},
            "site_url": f"https://myanimelist.net/character/{mal_id}" if mal_id else "",
            "anime_from": anime_from,
            "_source": "jikan",
        })
    # Enrich first result with full endpoint if possible
    if out and out[0].get("mal_id"):
        full = await jikan_get(f"characters/{out[0]['mal_id']}/full")
        if full and full.get("data"):
            d = full["data"]
            out[0]["about"] = d.get("about") or out[0]["about"]
            out[0]["images"] = d.get("images") or out[0]["images"]
            anime_list = d.get("anime") or []
            if anime_list:
                out[0]["anime_from"] = (
                    anime_list[0].get("anime", {}).get("title")
                    or anime_list[0].get("title")
                    or "Unknown"
                )
            out[0]["name"] = d.get("name") or out[0]["name"]
    return out[:limit]
