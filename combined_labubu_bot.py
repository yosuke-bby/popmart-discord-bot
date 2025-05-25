import discord
import asyncio
import aiohttp
import os
from datetime import datetime, timedelta, timezone

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

BLIND_BOX_URL = "https://prod-na-api.popmart.com/shop/v3/shop/productOnCollection"
POP_NOW_URL = "https://prod-na-api.popmart.com/shop/v1/box/box_set/extract"
POP_NOW_PAGE = "https://www.popmart.com/pages/popnow"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

blindbox_posted = {}
popnow_last_alert = None
cooldown_seconds = 60

async def check_blindboxes():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    async with aiohttp.ClientSession() as session:
        while not client.is_closed():
            try:
                async with session.get(BLIND_BOX_URL, timeout=10) as response:
                    data = await response.json()

                products = data.get("data", {}).get("items", [])
                now = datetime.now(timezone.utc)

                for product in products:
                    title = product.get("name", "No Title")
                    status = product.get("status", "")
                    available = status == "AVAILABLE"
                    product_url = f"https://popmart.com/product/{product.get('spuCode', '')}"
                    img_url = product.get("cover", "")

                    if available:
                        last_post = blindbox_posted.get(title, datetime.min.replace(tzinfo=timezone.utc))
                        if (now - last_post) > timedelta(seconds=cooldown_seconds):
                            embed = discord.Embed(
                                title=f"🚨 {title} is in stock!",
                                url=product_url,
                                description="Click fast before it disappears!"
                            )
                            if img_url:
                                embed.set_image(url=img_url)

                            await channel.send(embed=embed)
                            print(f"[{now.isoformat()}] POSTED BLINDBOX: {title}")
                            blindbox_posted[title] = now

            except Exception as e:
                print(f"Error checking Blind Box API: {e}")

            await asyncio.sleep(10)

async def check_popnow():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    global popnow_last_alert

    async with aiohttp.ClientSession() as session:
        while not client.is_closed():
            try:
                async with session.post(POP_NOW_URL, timeout=10) as response:
                    data = await response.json()

                box_list = data.get("data", {}).get("box_list", [])
                img_url = data.get("data", {}).get("set_main_pic", "")

                available_boxes = [box for box in box_list if box.get("state") == 1]

                if available_boxes:
                    now = datetime.now(timezone.utc)
                    if not popnow_last_alert or (now - popnow_last_alert) > timedelta(seconds=cooldown_seconds):
                        embed = discord.Embed(
                            title="🎉 Pop Now Labubu Boxes Available!",
                            description="Click below to grab one before it's gone!",
                            url=POP_NOW_PAGE
                        )
                        if img_url:
                            embed.set_image(url=img_url)

                        await channel.send(embed=embed)
                        print(f"[{now.isoformat()}] POSTED POPNOW ALERT")
                        popnow_last_alert = now

            except Exception as e:
                print(f"Error checking Pop Now API: {e}")

            await asyncio.sleep(10)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    asyncio.create_task(check_blindboxes())
    asyncio.create_task(check_popnow())

client.run(TOKEN)


