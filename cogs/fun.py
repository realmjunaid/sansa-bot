# ============================================
#   Sansa Bot — Fun Cog
#   Commands: /quote, /fact, /quiz
# ============================================

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import logging
import random
from config import (
    CHAT_CHANNEL_ID, COLOR_FUN, COLOR_ERROR
)

log = logging.getLogger("SansaBot.Fun")

# ── Anime Facts List ───────────────────────
ANIME_FACTS = [
    "🎌 The voice actor for Vegeta (Dragon Ball Z) and Naruto's father is the same person in the Japanese version!",
    "🎌 One Piece manga has been running since 1997 and is still ongoing!",
    "🎌 Naruto's creator Masashi Kishimoto failed many times while trying to draw Naruto!",
    "🎌 The idea for Titans in Attack on Titan came from a nightmare!",
    "🎌 Sword Art Online author Reki Kawahara wrote the first volume in just 10 days!",
    "🎌 Pokémon anime has been running since 1997 — over 25+ years!",
    "🎌 Studio Ghibli's Spirited Away was the first anime film to win an Oscar!",
    "🎌 Death Note's Light Yagami was originally designed slightly differently!",
    "🎌 Fullmetal Alchemist: Brotherhood is considered by many as the greatest anime of all time!",
    "🎌 My Hero Academia's Deku name actually comes from an insult!",
    "🎌 Demon Slayer's animation studio ufotable became world-famous in just a few years!",
    "🎌 Hunter x Hunter author Yoshihiro Togashi has taken long hiatuses due to health issues!",
    "🎌 Evangelion's Shinji was intentionally made weak and cowardly!",
    "🎌 Bleach, Naruto, and One Piece are collectively known as the 'Big Three'!",
    "🎌 Cowboy Bebop's soundtrack composer Yoko Kanno mixed every genre of music together!"
]

# ── Quiz Questions ─────────────────────────
QUIZ_QUESTIONS = [
    {
        "question": "What is Naruto's father's name?",
        "options": ["A. Jiraiya", "B. Minato Namikaze", "C. Kakashi", "D. Obito"],
        "answer": "B",
        "explanation": "Minato Namikaze, also known as the 'Yellow Flash of the Leaf'!"
    },
    {
        "question": "Which Devil Fruit did Luffy eat in One Piece?",
        "options": ["A. Mera Mera no Mi", "B. Gomu Gomu no Mi", "C. Yami Yami no Mi", "D. Gura Gura no Mi"],
        "answer": "B",
        "explanation": "Gomu Gomu no Mi — which gave him a rubber body!"
    },
    {
        "question": "Which Titan's power does Eren Yeager possess in Attack on Titan?",
        "options": ["A. Armored Titan", "B. Colossal Titan", "C. Attack Titan", "D. War Hammer Titan"],
        "answer": "C",
        "explanation": "Attack Titan — and later he gains War Hammer and Founding Titan powers too!"
    },
    {
        "question": "What was Light Yagami's alias in Death Note?",
        "options": ["A. L", "B. Near", "C. Kira", "D. Mello"],
        "answer": "C",
        "explanation": "Kira — a variation of the Japanese pronunciation of 'Killer'!"
    },
    {
        "question": "Which planet is Goku from in Dragon Ball Z?",
        "options": ["A. Earth", "B. Namek", "C. Planet Vegeta", "D. Frieza Planet"],
        "answer": "C",
        "explanation": "Planet Vegeta — Goku is actually a Saiyan, his real name is Kakarot!"
    },
    {
        "question": "Which breathing style does Tanjiro use in Demon Slayer?",
        "options": ["A. Thunder Breathing", "B. Water Breathing", "C. Flame Breathing", "D. Wind Breathing"],
        "answer": "B",
        "explanation": "Water Breathing — later he also masters Sun Breathing!"
    },
    {
        "question": "What did Edward Elric lose in Fullmetal Alchemist: Brotherhood?",
        "options": ["A. Both hands", "B. Both legs", "C. Left leg and right arm", "D. His eyes"],
        "answer": "C",
        "explanation": "His left leg during his mother's soul transmutation, and right arm to save his brother!"
    },
    {
        "question": "What is Deku's real name in My Hero Academia?",
        "options": ["A. Katsuki Bakugo", "B. Shoto Todoroki", "C. Izuku Midoriya", "D. Tenya Iida"],
        "answer": "C",
        "explanation": "Izuku Midoriya — who received One For All and dreams of becoming the No.1 Hero!"
    }
]

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("✅ Fun Cog loaded")

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

    # ── /quote ─────────────────────────────
    @app_commands.command(name="quote", description="💬 Show a random anime quote")
    async def quote(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://animechan.io/api/v1/quotes/random") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        quote_text = data.get("data", {}).get("content", "")
                        character = data.get("data", {}).get("character", {}).get("name", "Unknown")
                        anime = data.get("data", {}).get("anime", {}).get("name", "Unknown")

                        embed = discord.Embed(
                            description=f'*"{quote_text}"*',
                            color=COLOR_FUN
                        )
                        embed.set_author(name=f"💬 {character}")
                        embed.add_field(name="📺 Anime", value=anime, inline=True)
                        embed.set_footer(text="Sansa Bot 🌸 • Powered by Animechan")
                        await interaction.followup.send(embed=embed)
                        return
        except Exception as e:
            log.error(f"Quote fetch error: {e}")

        # Fallback quotes
        fallback_quotes = [
            {"quote": "Power comes in response to a need, not a desire.", "char": "Goku", "anime": "Dragon Ball Z"},
            {"quote": "If you don't take risks, you can't create a future.", "char": "Monkey D. Luffy", "anime": "One Piece"},
            {"quote": "Hard work is worthless for those that don't believe in themselves.", "char": "Naruto Uzumaki", "anime": "Naruto"},
            {"quote": "The world is not beautiful, therefore it is.", "char": "Kino", "anime": "Kino's Journey"},
            {"quote": "People's lives don't end when they die. It ends when they lose faith.", "char": "Itachi Uchiha", "anime": "Naruto"},
        ]
        q = random.choice(fallback_quotes)
        embed = discord.Embed(
            description=f'*"{q["quote"]}"*',
            color=COLOR_FUN
        )
        embed.set_author(name=f"💬 {q['char']}")
        embed.add_field(name="📺 Anime", value=q["anime"], inline=True)
        embed.set_footer(text="Sansa Bot 🌸")
        await interaction.followup.send(embed=embed)

    # ── /fact ──────────────────────────────
    @app_commands.command(name="fact", description="📖 Show a random anime fact")
    async def fact(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        fact = random.choice(ANIME_FACTS)

        embed = discord.Embed(
            title="📖 Anime Fact",
            description=fact,
            color=COLOR_FUN
        )
        embed.set_footer(text="Sansa Bot 🌸 • Did you know?")
        await interaction.response.send_message(embed=embed)

    # ── /quiz ──────────────────────────────
    @app_commands.command(name="quiz", description="🧠 Anime trivia quiz question")
    async def quiz(self, interaction: discord.Interaction):
        if not await self.check_channel(interaction):
            return

        q = random.choice(QUIZ_QUESTIONS)

        options_text = "\n".join(q["options"])

        embed = discord.Embed(
            title="🧠 Anime Quiz!",
            description=f"**{q['question']}**\n\n{options_text}",
            color=COLOR_FUN
        )
        embed.set_footer(text="Click the button below to answer!")

        # Answer buttons
        class QuizView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)
                self.answered = False

            async def handle_answer(self, interaction: discord.Interaction, choice: str):
                if self.answered:
                    await interaction.response.send_message("⏰ Already answered!", ephemeral=True)
                    return
                self.answered = True
                self.stop()

                if choice == q["answer"]:
                    result = discord.Embed(
                        title="✅ Correct Answer!",
                        description=f"**{q['explanation']}**",
                        color=0x2ECC71
                    )
                else:
                    result = discord.Embed(
                        title=f"❌ Wrong! Correct answer: {q['answer']}",
                        description=f"**{q['explanation']}**",
                        color=0xFF0000
                    )
                await interaction.response.send_message(embed=result)

            @discord.ui.button(label="A", style=discord.ButtonStyle.primary)
            async def btn_a(self, i, b): await self.handle_answer(i, "A")

            @discord.ui.button(label="B", style=discord.ButtonStyle.primary)
            async def btn_b(self, i, b): await self.handle_answer(i, "B")

            @discord.ui.button(label="C", style=discord.ButtonStyle.primary)
            async def btn_c(self, i, b): await self.handle_answer(i, "C")

            @discord.ui.button(label="D", style=discord.ButtonStyle.primary)
            async def btn_d(self, i, b): await self.handle_answer(i, "D")

        await interaction.response.send_message(embed=embed, view=QuizView())


async def setup(bot):
    await bot.add_cog(Fun(bot))
