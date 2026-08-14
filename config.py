# ============================================
#   Sansa Bot — Configuration File
#   এখানে তোমার Token এবং Channel IDs বসাও
# ============================================

import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot Token ──────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ── MyAnimeList API (https://myanimelist.net/apiconfig) ──
MAL_CLIENT_ID = os.getenv("MAL_CLIENT_ID", "")

# ── Channel IDs ────────────────────────────
ANIME_CHANNEL_ID = int(os.getenv("ANIME_CHANNEL_ID", 0))   # #anime-zone
MANGA_CHANNEL_ID = int(os.getenv("MANGA_CHANNEL_ID", 0))   # #manga-zone (auto)
MEMES_CHANNEL_ID = int(os.getenv("MEMES_CHANNEL_ID", 0))   # #memes-zone (auto)
CHAT_CHANNEL_ID  = int(os.getenv("CHAT_CHANNEL_ID",  0))   # #anime-chat
SAVE_CHANNEL_ID = int(os.getenv("SAVE_CHANNEL_ID", 0))   # #save (❤️ Save / ❌ Unsave feature)

# ── Bot Settings ───────────────────────────
BOT_PREFIX       = "/"
BOT_NAME         = "Sansa"
BOT_VERSION      = "1.0.0"
BOT_AUTHOR       = "Your Name"

# ── Auto Post Schedule ─────────────────────
# Anime posts every hour (24/day) - handled in auto.py via @tasks.loop(hours=1)

# ── Embed Colors ───────────────────────────
COLOR_WAIFU  = 0xFF69B4   # Pink
COLOR_ANIME  = 0x3498DB   # Blue
COLOR_MANGA  = 0x2ECC71   # Green
COLOR_MEMES  = 0xF1C40F   # Yellow
COLOR_FUN    = 0xE74C3C   # Red
COLOR_UTIL   = 0x9B59B6   # Purple
COLOR_ERROR  = 0xFF0000   # Red (error)

# ── Reddit (Memes) ─────────────────────────
REDDIT_SUBREDDITS = ["animememes", "goodanimemes", "animefunny"]
