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
cooldown_seconds = 30  # Time between duplicate notifications


async def check_popmart():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(BLIND_BOX_URL, timeout=60000)

        while not client.is_closed():
            try:
                await page.reload()
                await page.wait_for_selector(".product-grid-item", timeout=60000)

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
                            last_seen_stock[title] = "in_stock"
                            last_post_times[title] = now

                    elif not in_stock:
                        last_seen_stock[title] = "out_of_stock"

            except Exception as e:
                print(f"Error: {e}")

            await asyncio.sleep(2)  # Check every 2 seconds


async def main():
    async with client:
        await client.start(TOKEN)

async def startup():
    asyncio.create_task(check_popmart())
    await main()

asyncio.run(startup())



