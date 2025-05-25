import requests
import discord
import asyncio
import os
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# Your API endpoint (from DevTools)
API_URL = "https://www.popmart.com/_next/data/20250521180745/us/collection.json?id=18&FECU=fG1Yf2fDoMHi%2FakyIl5L5nDl9Czu%2FhtLLKTGjiHV0MkaMpCPzWt3plhoohI4WVifR4fHVOdm%2FwMz1kzFbC82w2AABG6bp1G1hNfe3LoYxbkNGJ9oFBCyE%2BabeoSCxbfnZtioUPlgeh%2FOQQDvpNyTBt2JA3%2FR8oUk1aL6%2B5Qx6poTEA%2FA6D%2BtECO%2FBj8t8byOxd"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

posted_items = {}
cooldown_seconds = 60


async def check_popmart_api():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            response = requests.get(API_URL)
            data = response.json()

            products = data.get("pageProps", {}).get("products", [])
            now = datetime.utcnow()

            for product in products:
                title = product.get("name", "No Title")
                available = product.get("status") == "AVAILABLE"
                product_url = f"https://www.popmart.com{product.get('url', '')}"
                img_url = product.get("cover", None)

                if available:
                    last_post = posted_items.get(title, datetime.min)
                    if (now - last_post) > timedelta(seconds=cooldown_seconds):
                        embed = discord.Embed(
                            title=f"🚨 {title} is in stock!",
                            url=product_url,
                            description="Click fast before it disappears!"
                        )
                        if img_url:
                            embed.set_image(url=img_url)
                        await channel.send(embed=embed)
                        print(f"[{now}] POSTED: {title}")
                        posted_items[title] = now
                else:
                    posted_items[title] = posted_items.get(title, datetime.min)

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
