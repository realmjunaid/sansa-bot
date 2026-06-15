# ============================================
#   Sansa Bot — Configuration File
#   এখানে তোমার Token এবং Channel IDs বসাও
# ============================================

import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot Token ──────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ── Channel IDs ────────────────────────────
WAIFU_CHANNEL_ID = int(os.getenv("WAIFU_CHANNEL_ID", 0))   # #waifu-zone
ANIME_CHANNEL_ID = int(os.getenv("ANIME_CHANNEL_ID", 0))   # #anime-zone
CHAT_CHANNEL_ID  = int(os.getenv("CHAT_CHANNEL_ID",  0))   # #anime-chat
HANIME_CHANNEL_ID = int(os.getenv("HANIME_CHANNEL_ID", 0))   # #hanime (auto NSFW posts + commands)
SAVE_CHANNEL_ID = int(os.getenv("SAVE_CHANNEL_ID", 0))   # #save (❤️ Save / ❌ Unsave feature)
HDAD_CHANNEL_ID = int(os.getenv("HDAD_CHANNEL_ID", 0))   # #hdad (auto NSFW every hour - hentaidad only)
SAKUH_CHANNEL_ID = int(os.getenv("SAKUH_CHANNEL_ID", 0))   # #sakuh (sakuhentai.net images + videos)
LUCI_CHANNEL_ID = int(os.getenv("LUCI_CHANNEL_ID", 0))   # #luci (lucioushentai.com)

# ── Bot Settings ───────────────────────────
BOT_PREFIX       = "/"
BOT_NAME         = "Sansa"
BOT_VERSION      = "1.0.0"
BOT_AUTHOR       = "Your Name"

# ── Auto Post Schedule ─────────────────────
WAIFU_AUTO_INTERVAL_HOURS = 1       # প্রতি ঘণ্টায় waifu post
# Anime posts every hour (24/day) - handled in auto.py via @tasks.loop(hours=1)

# ── Waifu Settings ─────────────────────────
WAIFU_TAGS = ["maid", "uniform", "selfie", "sexy"]

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
