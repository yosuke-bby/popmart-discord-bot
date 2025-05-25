import discord
import asyncio
import requests
import os
from datetime import datetime, timedelta, timezone

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

POP_NOW_URL = "https://prod-na-api.popmart.com/shop/v1/box/box_set/extract"
POP_NOW_PAGE = "https://www.popmart.com/pages/popnow"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last_alert = None
cooldown_seconds = 60

async def check_popnow_boxes():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            response = requests.post(POP_NOW_URL)
            data = response.json()

            box_list = data.get("data", {}).get("box_list", [])
            img_url = data.get("data", {}).get("set_main_pic", "")

            available_boxes = [box for box in box_list if box.get("state") == 1]

            if available_boxes:
                global last_alert
                now = datetime.now(timezone.utc)
                if not last_alert or (now - last_alert) > timedelta(seconds=cooldown_seconds):
                    embed = discord.Embed(
                        title="🎉 Pop Now Labubu Boxes Available!",
                        description="Run, don't walk — click below to grab a box before it's gone!",
                        url=POP_NOW_PAGE
                    )
                    if img_url:
                        embed.set_image(url=img_url)

                    await channel.send(embed=embed)
                    print(f"[{now.isoformat()}] ALERT POSTED")
                    last_alert = now

        except Exception as e:
            print(f"Error checking Pop Now API: {e}")

        await asyncio.sleep(10)

async def main():
    async with client:
        await client.start(TOKEN)

async def startup():
    asyncio.create_task(check_popnow_boxes())
    await main()

asyncio.run(startup())
