import discord
import asyncio
import os
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

print("Bot is starting...")

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
BLIND_BOX_URL = "https://popmart.com/collections/blind-box"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last_seen_stock = {}
last_post_times = {}
cooldown_seconds = 30  # Prevent reposting same item within this time


async def check_popmart():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    async with async_playwright() as p:
        # ✅ Switch to Firefox (more stable in some environments)
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page()

        # ✅ Spoof real browser headers
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0"
        })

        await page.goto(BLIND_BOX_URL, timeout=60000)

        # ✅ Print the page contents for debugging
        html = await page.content()
        print(f"🔎 PAGE HTML START\n{html[:1000]}\n🔍 PAGE HTML END")

        while not client.is_closed():
            try:
                try:
                    await page.wait_for_selector(".product-grid-item", timeout=60000, state="attached")
                except Exception as e:
                    print(f"⚠️ Could not find product grid: {e}")
                    await asyncio.sleep(5)
                    continue

                items = await page.query_selector_all(".product-grid-item")

                for item in items:
                    title_element = await item.query_selector(".product-title")
                    title = await title_element.inner_text() if title_element else "Unknown Title"

                    link_element = await item.query_selector("a")
                    product_link = await link_element.get_attribute("href") if link_element else BLIND_BOX_URL
                    product_url = f"https://popmart.com{product_link}" if product_link else BLIND_BOX_URL

                    img_element = await item.query_selector("img")
                    img_url = await img_element.get_attribute("src") if img_element else None

                    btn = await item.query_selector(".product-cart-button")
                    btn_text = await btn.inner_text() if btn else ""

                    in_stock = "add to cart" in btn_text.lower() or "pop now" in btn_text.lower()

                    print(f"[{datetime.utcnow()}] Checked: {title} → Button: '{btn_text.strip()}' → In Stock: {in_stock}")

                    if title not in last_seen_stock:
                        last_seen_stock[title] = "out_of_stock"

                    if in_stock and last_seen_stock[title] != "in_stock":
                        now = datetime.utcnow()
                        last_post_time = last_post_times.get(title, datetime.min)
                        if (now - last_post_time) > timedelta(seconds=cooldown_seconds):
                            embed = discord.Embed(
                                title=f"🚨 {title} is now available!",
                                url=product_url,
                                description="Click fast before it sells out!"
                            )
                            if img_url:
                                embed.set_image(url=img_url)
                            await channel.send(embed=embed)
                            print(f"🚨 POSTED TO DISCORD: {title} was detected IN STOCK!")
                            last_seen_stock[title] = "in_stock"
                            last_post_times[title] = now

                    elif not in_stock:
                        last_seen_stock[title] = "out_of_stock"

            except Exception as e:
                print(f"💥 Unexpected Error: {e}")

            await asyncio.sleep(2)


async def main():
    async with client:
        await client.start(TOKEN)

async def startup():
    asyncio.create_task(check_popmart())
    await main()

asyncio.run(startup())








