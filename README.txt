============================================
   SANSA BOT — Setup & Hosting Guide
   Version: 1.0.0
============================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STEP 1: Discord Bot তৈরি করো
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. https://discord.com/developers/applications এ যাও
2. "New Application" click করো
3. Name দাও: Sansa
4. "Bot" section এ যাও
5. "Reset Token" click করো → Token copy করো
6. নিচের সব Permission ON করো:
   ✅ Send Messages
   ✅ Embed Links
   ✅ Attach Files
   ✅ Read Message History
   ✅ Add Reactions
   ✅ Use Slash Commands
7. "Privileged Gateway Intents" থেকে ON করো:
   ✅ Message Content Intent
   ✅ Server Members Intent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STEP 2: Bot কে Server এ Add করো
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. "OAuth2" → "URL Generator" এ যাও
2. Scopes: ✅ bot ✅ applications.commands
3. Bot Permissions: ✅ Administrator
4. Generated URL copy করো → Browser এ open করো
5. তোমার server select করো → Authorize

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STEP 3: Channel IDs নাও
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Discord Settings → Advanced → Developer Mode: ON
2. তোমার server এ এই 3টি channel বানাও:
   • #waifu-zone
   • #anime-zone
   • #anime-chat
3. প্রতিটা channel এ Right Click → "Copy Channel ID"
4. তিনটা ID আলাদা করে রাখো

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STEP 4: .env File তৈরি করো
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

sansa-bot folder এ একটা ".env" নামের file বানাও:

BOT_TOKEN=তোমার_bot_token_এখানে
WAIFU_CHANNEL_ID=waifu_zone_channel_id
ANIME_CHANNEL_ID=anime_zone_channel_id
CHAT_CHANNEL_ID=anime_chat_channel_id

উদাহরণ:
BOT_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4.XXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXX
WAIFU_CHANNEL_ID=1234567890123456789
ANIME_CHANNEL_ID=1234567890123456790
CHAT_CHANNEL_ID=1234567890123456791

⚠️ সতর্কতা: .env file কখনো কাউকে দেবে না!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   STEP 5: Pterodactyl Panel এ Host করো
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Pterodactyl Panel এ Login করো
2. "New Server" বানাও
3. Egg: Python এবং Generic Python
4. Startup Command দাও:
   python bot.py
5. "File Manager" এ যাও
6. সব files upload করো:
   • bot.py
   • config.py
   • requirements.txt
   • .env
   • cogs/ folder (সব .py files সহ)

7. Console এ এই command দাও:
   pip install -r requirements.txt

8. Start button click করো ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   FILE STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

sansa-bot/
├── bot.py              ← Main file
├── config.py           ← Settings
├── requirements.txt    ← Dependencies
├── .env                ← Token & IDs (তুমি বানাবে)
└── cogs/
    ├── auto.py         ← Auto posting
    ├── waifu.py        ← Waifu commands
    ├── anime.py        ← Anime commands
    ├── manga.py        ← Manga commands
    ├── memes.py        ← Memes commands
    ├── fun.py          ← Fun commands
    └── utils.py        ← Utility commands

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   CHANNEL SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#waifu-zone  → শুধু auto waifu image (প্রতি ঘণ্টায়)
#anime-zone  → শুধু auto anime details (প্রতি ঘণ্টায় - 24/day via MyAnimeList/Jikan)
#anime-chat  → সব commands এখানে কাজ করে

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   COMMAND LIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌸 Waifu:
  /image              - Random waifu image
  /waifu <character>  - Specific character
  /tag <name>         - Tag দিয়ে image

🎌 Anime:
  /anime              - Random anime
  /anime <title>      - Specific anime
  /character <name>   - Character details
  /top                - Top 10 anime
  /season             - Current season

📚 Manga:
  /manga              - Random manga
  /manga <title>      - Specific manga

😂 Memes:
  /memes              - Random meme
  /memes hot          - Hot memes
  /memes new          - Latest memes
  /memes funny        - Funny memes

🎉 Fun:
  /quote              - Anime quote
  /fact               - Anime fact
  /quiz               - Trivia quiz

⚙️ Utility:
  /help               - Command list
  /ping               - Bot latency
  /status             - Bot status
  /schedule           - Next auto post
  /count              - Today's count

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   PROBLEM? SOLUTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Bot online কিন্তু commands কাজ করছে না?
   → 1-2 মিনিট অপেক্ষা করো (slash command sync হতে সময় লাগে)

❌ Bot start হচ্ছে না?
   → .env file ঠিকমতো বানানো হয়েছে কিনা দেখো
   → pip install -r requirements.txt দিয়েছো কিনা দেখো

❌ Auto post হচ্ছে না?
   → Channel IDs সঠিক কিনা দেখো
   → Bot এর channel এ permission আছে কিনা দেখো

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Sansa Bot v1.0.0 🌸
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
