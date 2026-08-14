# Sansa Bot 🌸

**A Discord bot for anime, manga, memes, and fun — powered by MyAnimeList.**

| | |
|---|---|
| **Version** | 1.0.0 |
| **Language** | Python 3.10+ |
| **Library** | [discord.py](https://github.com/Rapptz/discord.py) 2.x |
| **Data source** | [MyAnimeList API](https://myanimelist.net/apiconfig) (primary) · Jikan / AniList (fallback) |

---

## Table of contents · সূচিপত্র

1. [English documentation](#english-documentation)
2. [বাংলা ডকুমেন্টেশন](#বাংলা-ডকুমেন্টেশন)

---

# English documentation

## Overview

**Sansa** is a slash-command Discord bot built for anime communities. It can:

- Look up **anime** and **manga** details (score, episodes/chapters, genres, cover art)
- Show **top 10**, **current season**, and **character** info
- Estimate total **watch time** for a series
- Find basic **streaming page links**
- Post random **anime memes**, **quotes**, **facts**, and a simple **quiz**
- **Auto-post** anime, manga, and memes every hour to dedicated channels
- Let users **save** bot embeds with a ❤️ reaction

Most interactive commands only work in your main chat channel (e.g. `#anime-chat`) so the rest of the server stays clean.

---

## Features

### Anime
| Command | Description |
|---------|-------------|
| `/anime` | Random anime details |
| `/anime <title>` | Search a specific title |
| `/character <name>` | Character bio + image |
| `/top` | Top 10 anime (MyAnimeList ranking) |
| `/season` | Current season anime list |
| `/watchtime <title>` | Total watch time calculator |
| `/watchlink <title>` | Streaming page links (best-effort) |

### Manga
| Command | Description |
|---------|-------------|
| `/manga` | Random manga details |
| `/manga <title>` | Search a specific title |

### Memes
| Command | Description |
|---------|-------------|
| `/memes` | Random anime meme |
| `/memes hot` | Hot memes |
| `/memes new` | Latest memes |
| `/memes funny` | Funny memes |

### Fun
| Command | Description |
|---------|-------------|
| `/quote` | Random anime quote |
| `/fact` | Random anime fact |
| `/quiz` | Short anime trivia quiz |

### Utility
| Command | Description |
|---------|-------------|
| `/help` | Friendly command list |
| `/commands` | Live slash-command list from the bot |
| `/ping` | Latency |
| `/status` | Bot status |
| `/schedule` | Next auto-post countdown |
| `/count` | Today’s auto-post counts |

### Auto posts (no command needed)
| Channel (example name) | What happens |
|------------------------|--------------|
| `#anime-zone` | Random anime embed every **1 hour** |
| `#manga-zone` | Random manga embed every **1 hour** |
| `#memes-zone` | Anime meme every **1 hour** |

### Save feature
1. React with **❤️** on any message posted by Sansa → a copy is sent to your `#save` channel.
2. In `#save`, the bot owner can react **❌** to remove a saved message.

---

## Channel layout

Create these channels (names can differ; IDs matter):

| Env variable | Typical channel | Purpose |
|--------------|-----------------|---------|
| `CHAT_CHANNEL_ID` | `#anime-chat` | All slash commands |
| `ANIME_CHANNEL_ID` | `#anime-zone` | Hourly anime auto-post |
| `MANGA_CHANNEL_ID` | `#manga-zone` | Hourly manga auto-post |
| `MEMES_CHANNEL_ID` | `#memes-zone` | Hourly meme auto-post |
| `SAVE_CHANNEL_ID` | `#save` | ❤️ saved embeds |

---

## Project structure

```text
sansa-bot/
├── bot.py              # Entry point, intents, slash sync, save reactions
├── config.py           # Loads .env → settings & embed colors
├── requirements.txt    # Python dependencies
├── .env.example        # Template for secrets (copy to .env)
├── .gitignore
├── README.md
└── cogs/
    ├── mal_client.py   # Official MyAnimeList API v2 client
    ├── anime.py        # Anime slash commands
    ├── manga.py        # Manga slash commands
    ├── auto.py         # Hourly auto-posts
    ├── memes.py        # Meme commands
    ├── fun.py          # Quote / fact / quiz
    └── utils.py        # Help, ping, status, schedule, count
```

---

## Requirements

- **Python 3.10+** (3.11 or 3.12 recommended)
- A **Discord bot application** with a token
- A free **MyAnimeList API Client ID** ([get one here](https://myanimelist.net/apiconfig))
- Discord channels + **Developer Mode** enabled (to copy channel IDs)

---

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/sansa-bot.git
cd sansa-bot
```

### 2. Create a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env` and fill in real values:

```env
BOT_TOKEN=your_discord_bot_token
MAL_CLIENT_ID=your_mal_client_id

CHAT_CHANNEL_ID=123456789012345678
ANIME_CHANNEL_ID=123456789012345678
MANGA_CHANNEL_ID=123456789012345678
MEMES_CHANNEL_ID=123456789012345678
SAVE_CHANNEL_ID=123456789012345678
```

> **Never commit `.env` to GitHub.** It is already listed in `.gitignore`.

### 5. Run the bot

```bash
python bot.py
```

When you see logs like `Sansa Bot is online!` and `Synced N slash command(s)`, the bot is ready. Slash commands may take up to a minute to appear in Discord the first time.

---

## Discord developer setup (detailed)

### Create the bot

1. Open [Discord Developer Portal](https://discord.com/developers/applications).
2. **New Application** → name it (e.g. `Sansa`).
3. Go to **Bot** → **Reset Token** → copy the token into `BOT_TOKEN`.
4. Under **Privileged Gateway Intents**, enable:
   - **Message Content Intent**
5. Enable bot permissions as needed: Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions, Use Application Commands.

### Invite the bot

1. **OAuth2 → URL Generator**
2. Scopes: `bot` + `applications.commands`
3. Permissions: at least the ones above (or Administrator for simple private servers)
4. Open the generated URL → select your server → Authorize

### Get channel IDs

1. Discord **User Settings → Advanced → Developer Mode → ON**
2. Right-click each channel → **Copy Channel ID**
3. Paste into `.env`

### MyAnimeList API key

1. Log in at [myanimelist.net/apiconfig](https://myanimelist.net/apiconfig)
2. Create an API client / app
3. Copy the **Client ID** into `MAL_CLIENT_ID`

If `MAL_CLIENT_ID` is missing, the bot still runs and falls back to **Jikan** (unofficial MAL mirror) and **AniList** where possible.

---

## Hosting

### Local PC

```bash
python bot.py
```

Keep the terminal open, or run under a process manager (`pm2`, `nssm`, `systemd`, etc.).

### Pterodactyl / VPS panel

1. Create a server with a **Python** egg.
2. Startup command: `python bot.py`
3. Upload project files (`bot.py`, `config.py`, `requirements.txt`, `.env`, `cogs/`).
4. Install deps: `pip install -r requirements.txt`
5. Start the server.

### Environment checklist before go-live

- [ ] `BOT_TOKEN` is valid  
- [ ] `MAL_CLIENT_ID` is set (recommended)  
- [ ] All channel IDs are correct  
- [ ] Bot can **View Channel**, **Send Messages**, and **Embed Links** in those channels  
- [ ] Bot is online and slash commands are synced  

---

## How data sources work

```text
Anime / Manga lookup
        │
        ▼
 MyAnimeList API  ──(if no key / error)──►  Jikan  ──►  AniList
```

- **Scores from MAL / Jikan:** out of **10**  
- **Scores from AniList fallback:** out of **100**  
- Embed footers show which source was used when available  

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Bot online but no slash commands | Wait 1–2 minutes; restart bot; ensure invite included `applications.commands` |
| Bot crashes on start | Check `.env` exists; run `pip install -r requirements.txt`; verify `BOT_TOKEN` |
| Commands say “only works in #…” | Use the channel matching `CHAT_CHANNEL_ID` |
| Auto-posts never appear | Check `ANIME_CHANNEL_ID` / `MANGA_CHANNEL_ID` / `MEMES_CHANNEL_ID` and bot permissions |
| MAL data missing | Set a valid `MAL_CLIENT_ID`; bot will use fallbacks without it |
| ❤️ save does nothing | Set `SAVE_CHANNEL_ID`; react on a **bot** message, not a user message |

---

## Security notes

- Do **not** share your bot token or commit `.env`.
- If a token leaks, **reset it** immediately in the Discord Developer Portal.
- Prefer least-privilege bot permissions on public servers.

---

## License & credits

- Built for personal / community Discord servers.
- Anime & manga metadata © respective rights holders; data via **MyAnimeList**, **Jikan**, and **AniList** APIs.
- Memes / quotes come from third-party public APIs used by the bot.

---
---

# বাংলা ডকুমেন্টেশন

## সংক্ষিপ্ত পরিচিতি

**Sansa** একটি Discord বট — অ্যানিমে কমিউনিটির জন্য বানানো। স্ল্যাশ কমান্ড (`/anime`, `/manga` ইত্যাদি) দিয়ে কাজ করে।

বট দিয়ে যা করা যায়:

- অ্যানিমে ও মাঙ্গার **বিস্তারিত তথ্য** (স্কোর, এপিসোড/চ্যাপ্টার, জেনার, কভার ছবি)
- **টপ ১০**, **চলতি সিজন**, **ক্যারেক্টার** খোঁজা
- সিরিজের **মোট ওয়াচ টাইম** হিসাব
- স্ট্রিমিং পেজ লিংক খোঁজা (যতটুকু সম্ভব)
- অ্যানিমে **মিম**, **কোট**, **ফ্যাক্ট**, ছোট **কুইজ**
- প্রতি ঘণ্টায় আলাদা চ্যানেলে **অটো পোস্ট** (অ্যানিমে / মাঙ্গা / মিম)
- বটের মেসেজে **❤️** দিয়ে **সেভ** করা

বেশিরভাগ কমান্ড শুধু মূল চ্যাট চ্যানেলে (যেমন `#anime-chat`) কাজ করে — যাতে অন্য চ্যানেলগুলো পরিষ্কার থাকে।

---

## ফিচার তালিকা

### অ্যানিমে কমান্ড
| কমান্ড | কাজ |
|--------|-----|
| `/anime` | র‍্যান্ডম অ্যানিমে |
| `/anime <title>` | নির্দিষ্ট অ্যানিমে সার্চ |
| `/character <name>` | ক্যারেক্টারের তথ্য + ছবি |
| `/top` | টপ ১০ অ্যানিমে (MyAnimeList) |
| `/season` | চলতি সিজনের লিস্ট |
| `/watchtime <title>` | মোট দেখার সময় |
| `/watchlink <title>` | স্ট্রিমিং লিংক (best-effort) |

### মাঙ্গা
| কমান্ড | কাজ |
|--------|-----|
| `/manga` | র‍্যান্ডম মাঙ্গা |
| `/manga <title>` | নির্দিষ্ট মাঙ্গা সার্চ |

### মিম
| কমান্ড | কাজ |
|--------|-----|
| `/memes` | র‍্যান্ডম অ্যানিমে মিম |
| `/memes hot` | হট মিম |
| `/memes new` | নতুন মিম |
| `/memes funny` | মজার মিম |

### ফান
| কমান্ড | কাজ |
|--------|-----|
| `/quote` | অ্যানিমে কোট |
| `/fact` | অ্যানিমে ফ্যাক্ট |
| `/quiz` | ছোট ট্রিভিয়া কুইজ |

### ইউটিলিটি
| কমান্ড | কাজ |
|--------|-----|
| `/help` | সব কমান্ডের তালিকা |
| `/commands` | বট থেকে লাইভ কমান্ড লিস্ট |
| `/ping` | লেটেন্সি |
| `/status` | বট স্ট্যাটাস |
| `/schedule` | পরবর্তী অটো পোস্ট কখন |
| `/count` | আজকের অটো পোস্ট সংখ্যা |

### অটো পোস্ট (কমান্ড লাগে না)
| চ্যানেল (উদাহরণ নাম) | কী হয় |
|----------------------|--------|
| `#anime-zone` | প্রতি **১ ঘণ্টায়** র‍্যান্ডম অ্যানিমে |
| `#manga-zone` | প্রতি **১ ঘণ্টায়** র‍্যান্ডম মাঙ্গা |
| `#memes-zone` | প্রতি **১ ঘণ্টায়** অ্যানিমে মিম |

### সেভ ফিচার
1. Sansa-এর কোনো মেসেজে **❤️** রিঅ্যাক্ট করলে সেটা `#save` চ্যানেলে কপি হয়।  
2. `#save`-এ বট ওনার **❌** দিয়ে সেভ করা মেসেজ মুছতে পারেন।

---

## কোন চ্যানেলে কী

| `.env` ভ্যারিয়েবল | সাধারণ চ্যানেল নাম | কাজ |
|--------------------|---------------------|-----|
| `CHAT_CHANNEL_ID` | `#anime-chat` | সব স্ল্যাশ কমান্ড |
| `ANIME_CHANNEL_ID` | `#anime-zone` | ঘণ্টায় অ্যানিমে অটো পোস্ট |
| `MANGA_CHANNEL_ID` | `#manga-zone` | ঘণ্টায় মাঙ্গা অটো পোস্ট |
| `MEMES_CHANNEL_ID` | `#memes-zone` | ঘণ্টায় মিম অটো পোস্ট |
| `SAVE_CHANNEL_ID` | `#save` | ❤️ সেভ করা কনটেন্ট |

> চ্যানেলের **নাম** যা খুশি হতে পারে — গুরুত্বপূর্ণ হলো **Channel ID** সঠিকভাবে `.env`-এ দেওয়া।

---

## প্রজেক্ট ফোল্ডার স্ট্রাকচার

```text
sansa-bot/
├── bot.py              # মেইন ফাইল — বট চালু, কগ লোড, সেভ রিঅ্যাকশন
├── config.py           # .env থেকে সেটিংস লোড
├── requirements.txt    # পাইথন প্যাকেজ
├── .env.example        # সিক্রেট টেমপ্লেট (কপি করে .env বানাবেন)
├── .gitignore
├── README.md
└── cogs/
    ├── mal_client.py   # অফিসিয়াল MyAnimeList API
    ├── anime.py        # অ্যানিমে কমান্ড
    ├── manga.py        # মাঙ্গা কমান্ড
    ├── auto.py         # অটো পোস্ট
    ├── memes.py        # মিম
    ├── fun.py          # কোট / ফ্যাক্ট / কুইজ
    └── utils.py        # হেল্প, পিং, স্ট্যাটাস ইত্যাদি
```

---

## যা লাগবে

- **Python 3.10+** (৩.১১ বা ৩.১২ ভালো)
- Discord **Bot Token**
- ফ্রি **MyAnimeList Client ID** — [এখান থেকে নিন](https://myanimelist.net/apiconfig)
- সার্ভারে প্রয়োজনীয় চ্যানেল + Discord-এ **Developer Mode** চালু (Channel ID কপি করতে)

---

## সহজ সেটআপ (ধাপে ধাপে)

### ১) রিপো ক্লোন

```bash
git clone https://github.com/YOUR_USERNAME/sansa-bot.git
cd sansa-bot
```

### ২) ভার্চুয়াল এনভায়রনমেন্ট (সাজেস্টেড)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### ৩) প্যাকেজ ইনস্টল

```bash
pip install -r requirements.txt
```

### ৪) `.env` ফাইল বানান

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

`.env` খুলে আসল মান দিন:

```env
BOT_TOKEN=আপনার_ডিসকর্ড_বট_টোকেন
MAL_CLIENT_ID=আপনার_MAL_ক্লায়েন্ট_আইডি

CHAT_CHANNEL_ID=১২৩৪৫৬৭৮৯০১২৩৪৫৬৭৮
ANIME_CHANNEL_ID=...
MANGA_CHANNEL_ID=...
MEMES_CHANNEL_ID=...
SAVE_CHANNEL_ID=...
```

> **সতর্কতা:** `.env` কখনো GitHub-এ আপলোড করবেন না। টোকেন লিক হলে সাথে সাথে রিসেট করুন।

### ৫) বট চালান

```bash
python bot.py
```

কনসোলে `online` ও `Synced ... slash command` দেখলে প্রস্তুত। প্রথমবার Discord-এ কমান্ড আসতে ১–২ মিনিট লাগতে পারে।

---

## Discord বট তৈরি (বিস্তারিত)

### বট অ্যাপ

1. [Discord Developer Portal](https://discord.com/developers/applications) খুলুন  
2. **New Application** → নাম দিন (যেমন `Sansa`)  
3. **Bot** → **Reset Token** → টোকেন কপি করে `BOT_TOKEN`-এ দিন  
4. **Privileged Gateway Intents** থেকে **Message Content Intent** চালু করুন  
5. প্রয়োজনীয় পারমিশন: Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions, Use Application Commands  

### সার্ভারে ইনভাইট

1. **OAuth2 → URL Generator**  
2. Scopes: `bot` + `applications.commands`  
3. Permissions বেছে নিন (প্রাইভেট সার্ভারে Administrator সহজ)  
4. লিংক খুলে সার্ভার সিলেক্ট → Authorize  

### Channel ID নেওয়া

1. Discord **Settings → Advanced → Developer Mode → ON**  
2. চ্যানেলে রাইট-ক্লিক → **Copy Channel ID**  
3. `.env`-এ পেস্ট  

### MyAnimeList API

1. [myanimelist.net/apiconfig](https://myanimelist.net/apiconfig) এ লগইন  
2. নতুন API ক্লায়েন্ট/অ্যাপ তৈরি  
3. **Client ID** কপি → `MAL_CLIENT_ID`  

`MAL_CLIENT_ID` না দিলেও বট চলবে; তখন **Jikan** ও **AniList** ফলব্যাক ব্যবহার করবে।

---

## হোস্টিং

### নিজের পিসি

```bash
python bot.py
```

টার্মিনাল খোলা রাখতে হবে, অথবা `pm2` / Windows Service / `systemd` দিয়ে ব্যাকগ্রাউন্ডে চালান।

### Pterodactyl / VPS প্যানেল

1. Python egg দিয়ে সার্ভার বানান  
2. Startup: `python bot.py`  
3. ফাইল আপলোড: `bot.py`, `config.py`, `requirements.txt`, `.env`, `cogs/`  
4. `pip install -r requirements.txt`  
5. Start  

### লাইভ করার আগে চেকলিস্ট

- [ ] `BOT_TOKEN` ঠিক আছে  
- [ ] `MAL_CLIENT_ID` দেওয়া আছে (রিকমেন্ডেড)  
- [ ] সব Channel ID সঠিক  
- [ ] ওই চ্যানেলগুলোতে বটের View / Send / Embed পারমিশন আছে  
- [ ] বট অনলাইন + স্ল্যাশ কমান্ড সিঙ্ক হয়েছে  

---

## ডেটা কোথা থেকে আসে

```text
অ্যানিমে / মাঙ্গা সার্চ
        │
        ▼
 MyAnimeList API  ──(কী নেই / এরর)──►  Jikan  ──►  AniList
```

- **MAL / Jikan স্কোর:** **১০**-এর মধ্যে  
- **AniList ফলব্যাক স্কোর:** **১০০**-এর মধ্যে  
- এম্বেড ফুটারে সোর্সের নাম দেখা যায় (যেখানে সেট করা আছে)  

---

## সমস্যা ও সমাধান

| সমস্যা | কী করবেন |
|--------|----------|
| বট অনলাইন কিন্তু কমান্ড নেই | ১–২ মিনিট অপেক্ষা; রিস্টার্ট; ইনভাইটে `applications.commands` ছিল কিনা দেখুন |
| স্টার্টই হচ্ছে না | `.env` আছে কিনা; `pip install -r requirements.txt`; টোকেন চেক |
| “শুধু #anime-chat-এ কাজ করে” | `CHAT_CHANNEL_ID` যে চ্যানেল, সেখানে কমান্ড দিন |
| অটো পোস্ট আসছে না | Zone চ্যানেল ID + বট পারমিশন চেক করুন |
| MAL ডেটা আসছে না | সঠিক `MAL_CLIENT_ID` দিন; না থাকলে ফলব্যাক চলবে |
| ❤️ সেভ হচ্ছে না | `SAVE_CHANNEL_ID` সেট করুন; **বটের** মেসেজে রিঅ্যাক্ট করুন |

---

## নিরাপত্তা

- টোকেন ও `.env` **কাউকে দেবেন না**, GitHub-এ পুশ করবেন না।  
- লিক হলে Developer Portal থেকে টোকেন **রিসেট** করুন।  
- পাবলিক সার্ভারে অপ্রয়োজনীয় অ্যাডমিন পারমিশন এড়িয়ে চলুন।  

---

## ক্রেডিট

- অ্যানিমে/মাঙ্গা তথ্য সংশ্লিষ্ট কপিরাইটধারীদের; ডেটা **MyAnimeList**, **Jikan**, **AniList** API থেকে।  
- মিম/কোট থার্ড-পার্টি পাবলিক API ব্যবহার করে।  

---

## সাপোর্ট

ইস্যু বা সাজেশন থাকলে GitHub-এ Issue খুলুন, অথবা রিপো মেইনটেইনারকে জানান।

**Sansa Bot v1.0.0** — Enjoy your anime server 🌸
