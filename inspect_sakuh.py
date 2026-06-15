import aiohttp
import asyncio
from bs4 import BeautifulSoup
async def inspect():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get("https://www.sakuhentai.net/hentai-gallery/page/2/", timeout=20) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "lxml")
            print("Title:", soup.title.string if soup.title else "no")
            imgs = soup.find_all("img")
            print("Total imgs:", len(imgs))
            for i, img in enumerate(imgs[:30]):
                src = (img.get("src") or img.get("data-src") or img.get("data-lazy-src") or "").strip()
                cls = " ".join(img.get("class", [])) if img.get("class") else ""
                parent_tag = img.parent.name if img.parent else "none"
                print(f"{i}: src={src[:100]} class=[{cls}] parent={parent_tag}")
asyncio.run(inspect())
