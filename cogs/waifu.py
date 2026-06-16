import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import logging
from config import COLOR_WAIFU

log = logging.getLogger("SansaBot.Waifu")

class Waifu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_waifu_images(self, count: int = 15):
        images = []
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            tags = "1girl solo rating:s"
            url = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit={max(count, 20)}&tags={tags}"
            async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}, timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        posts = data if isinstance(data, list) else data.get("post", []) if isinstance(data, dict) else []
                        log.info(f"[Waifu] Safebooru (sfw) returned {len(posts)} posts")
                        random.shuffle(posts)
                        for post in posts:
                            image_url = post.get("file_url") or post.get("sample_url")
                            if image_url and not any(i["url"] == image_url for i in images):
                                images.append({"url": image_url})
                            if len(images) >= count:
                                break
                    else:
                        log.warning(f"[Waifu] Safebooru sfw bad status: {resp.status}")
        except Exception as e:
            log.warning(f"[Waifu] Safebooru waifu batch failed: {e}")

        if len(images) >= count:
            log.info(f"[Waifu] Returning {len(images)} sfw images (mostly Safebooru)")
            return images[:count]

        fallbacks = [
            "https://nekos.best/api/v2/neko",
            "https://api.purrbot.site/v2/img/sfw/neko/img",
        ]
        attempts = 0
        while len(images) < count and attempts < count * 2:
            attempts += 1
            try:
                fb = random.choice(fallbacks)
                async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}, timeout=timeout) as session:
                    async with session.get(fb) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            url = None
                            if "nekos.best" in fb:
                                results = data.get("results", [])
                                if results:
                                    url = results[0].get("url")
                            elif "purrbot" in fb:
                                url = data.get("link")
                            if url and not any(i["url"] == url for i in images):
                                images.append({"url": url})
            except Exception as e:
                log.debug(f"[Waifu] fallback attempt err: {e}")
                continue
        log.info(f"[Waifu] Returning {len(images)} images after fallbacks")
        return images[:count]

    async def fetch_ecchi_waifu_images(self, count: int = 15):
        images = []
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            tags = "1girl solo"
            url = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit={max(count, 30)}&tags={tags}"
            async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}, timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        posts = data if isinstance(data, list) else data.get("post", []) if isinstance(data, dict) else []
                        log.info(f"[Waifu] Safebooru (ecchi) returned {len(posts)} posts")
                        random.shuffle(posts)
                        for post in posts:
                            image_url = post.get("file_url") or post.get("sample_url")
                            if image_url and not any(i["url"] == image_url for i in images):
                                images.append({"url": image_url})
                            if len(images) >= count:
                                break
                    else:
                        log.warning(f"[Waifu] Safebooru ecchi bad status: {resp.status}")
        except Exception as e:
            log.warning(f"[Waifu] Safebooru ecchi batch failed: {e}")

        while len(images) < count:
            more = await self.fetch_waifu_images(count - len(images))
            for m in more:
                if len(images) >= count:
                    break
                if not any(i["url"] == m["url"] for i in images):
                    images.append(m)
            break
        log.info(f"[Waifu] Returning {len(images)} ecchi images")
        return images[:count]

    @app_commands.command(name="image", description="Random waifu image")
    async def image(self, interaction: discord.Interaction):
        images = await self.fetch_waifu_images(count=1)
        if not images:
            await interaction.response.send_message("❌ Waifu source down", ephemeral=True)
            return
        embed = discord.Embed(color=0xFF69B4)
        embed.set_image(url=images[0]["url"])
        await interaction.response.send_message(embed=embed)
        log.info(f"[Waifu] /image posted")

    @app_commands.command(name="waifu", description="Random ecchi waifu images (15)")
    async def waifu_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        images = await self.fetch_ecchi_waifu_images(count=15)
        if not images:
            await interaction.followup.send("❌ No images")
            return
        for img in images:
            e = discord.Embed(color=0xFF69B4)
            e.set_image(url=img["url"])
            await interaction.followup.send(embed=e)
        log.info(f"[Waifu] /waifu posted {len(images)} images")

    @app_commands.command(name="tag", description="Get waifu image by tag")
    @app_commands.describe(name="Tag like maid, school, bikini etc")
    async def tag(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        images = []
        try:
            t = name.replace(" ", "_").lower()
            url = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=5&tags=1girl+{t}"
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(headers={"User-Agent": "SansaBot/1.0"}, timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        posts = data if isinstance(data, list) else data.get("post", []) if isinstance(data, dict) else []
                        for p in posts:
                            u = p.get("file_url") or p.get("sample_url")
                            if u:
                                images.append({"url": u})
                                break
        except Exception:
            pass
        if not images:
            images = await self.fetch_waifu_images(1)
        if images:
            embed = discord.Embed(color=0xFF69B4)
            embed.set_image(url=images[0]["url"])
            await interaction.followup.send(embed=embed)
            log.info(f"[Waifu] /tag {name} posted")
        else:
            await interaction.followup.send("❌ No image found", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Waifu(bot))
    log.info("✅ Waifu Cog loaded (fetch_waifu_images + /image /waifu /tag ready)")
