import requests
import discord
import asyncio
import os
from datetime import datetime, timedelta, timezone

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)

posted_items = {}
cooldown_seconds = 60

async def check_popmart_api():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            now = datetime.now(timezone.utc)

            # 👇 FAKE product data to simulate a restock
            products = [{
                "name": "FAKE TEST ITEM",
                "status": "AVAILABLE",
                "spuCode": "fake-test-item",
                "cover": "https://media.tenor.com/2roX3uxz_68AAAAd/cat-space.gif"
            }]

            for product in products:
                title = product.get("name", "No Title")
                status = product.get("status", "")
                available = status == "AVAILABLE"
                product_url = f"https://popmart.com/product/{product.get('spuCode', '')}"
                img_url = product.get("cover", "")

                if available:
                    last_post = posted_items.get(title, datetime.min.replace(tzinfo=timezone.utc))
                    if (now - last_post) > timedelta(seconds=cooldown_seconds):
                        embed = discord.Embed(
                            title=f"🚨 {title} is in stock!",
                            url=product_url,
                            description="Click fast before it disappears!"
                        )
                        if img_url:
                            embed.set_image(url=img_url)

                        await channel.send(embed=embed)
                        print(f"[{now.isoformat()}] POSTED: {title}")
                        posted_items[title] = now

        except Exception as e:
            print(f"Error checking API: {e}")

        await asyncio.sleep(10)

async def main():
    async with client:
        await client.start(TOKEN)

async def startup():
    asyncio.create_task(check_popmart_api())
    await main()

asyncio.run(startup())



