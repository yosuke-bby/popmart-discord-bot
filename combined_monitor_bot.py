import discord
import asyncio
import aiohttp
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

TOKEN = os.getenv("TOKEN")
POP_CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
AMAZON_CHANNEL_ID = int(os.getenv("AMAZON_CHANNEL_ID"))

BLIND_BOX_URL = "https://prod-na-api.popmart.com/shop/v3/shop/productOnCollection"
POP_NOW_URL = "https://prod-na-api.popmart.com/shop/v1/box/box_set/extract"
POP_NOW_PAGE = "https://www.popmart.com/pages/popnow"

AMAZON_URLS = [
    "https://www.amazon.com/POP-MART-Big-into-Energy/dp/B0DT44TSM2?th=1",
    "https://www.amazon.com/POP-MART-Big-into-Energy/dp/B0DT41V371?ref_=ast_sto_dp&th=1",
    "https://www.amazon.com/POP-MART-Monsters-Collectible-Accessories/dp/B0CL6PLZ3Y?th=1"
]

intents = discord.Intents.default()
client = discord.Client(intents=intents)

blindbox_posted = {}
popnow_last_alert = None
amazon_posted = {}
cooldown_seconds = 60

async def check_blindboxes():
    await client.wait_until_ready()
    channel = client.get_channel(POP_CHANNEL_ID)

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
                                title=f"🧸 Restock Detected: {title}",
                                url=product_url,
                                description="**Status:** In Stock
**Store:** popmart.com",
                                color=discord.Color.green()
                            )
                            embed.set_footer(text=f"Pop Mart Monitor | Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                            if img_url:
                                embed.set_thumbnail(url=img_url)

                            await channel.send(embed=embed)
                            print(f"[{now.isoformat()}] POSTED BLINDBOX: {title}")
                            blindbox_posted[title] = now

            except Exception as e:
                print(f"Error checking Blind Box API: {e}")

            await asyncio.sleep(10)

async def check_popnow():
    await client.wait_until_ready()
    channel = client.get_channel(POP_CHANNEL_ID)

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
                            url=POP_NOW_PAGE,
                            description="**Status:** In Stock
**Store:** popmart.com",
                            color=discord.Color.green()
                        )
                        embed.set_footer(text=f"Pop Mart Monitor | Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                        if img_url:
                            embed.set_thumbnail(url=img_url)

                        await channel.send(embed=embed)
                        print(f"[{now.isoformat()}] POSTED POPNOW ALERT")
                        popnow_last_alert = now

            except Exception as e:
                print(f"Error checking Pop Now API: {e}")

            await asyncio.sleep(10)

async def check_amazon():
    await client.wait_until_ready()
    channel = client.get_channel(AMAZON_CHANNEL_ID)

    async with aiohttp.ClientSession() as session:
        while not client.is_closed():
            for url in AMAZON_URLS:
                try:
                    async with session.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as response:
                        text = await response.text()
                        soup = BeautifulSoup(text, "html.parser")

                        title_tag = soup.select_one("#productTitle")
                        title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

                        price_tag = soup.select_one(".a-price .a-offscreen")
                        price = price_tag.get_text(strip=True) if price_tag else "Unavailable"

                        img_tag = soup.select_one("#landingImage")
                        img_url = img_tag["src"] if img_tag else None

                        availability = soup.select_one("#availability")
                        availability_text = availability.get_text(strip=True).lower() if availability else ""
                        in_stock = "in stock" in availability_text and "currently unavailable" not in availability_text

                        if in_stock:
                            last_post = amazon_posted.get(url, datetime.min.replace(tzinfo=timezone.utc))
                            now = datetime.now(timezone.utc)
                            if (now - last_post) > timedelta(seconds=cooldown_seconds):
                                embed = discord.Embed(
                                    title="📦 Restock Detected",
                                    url=url,
                                    description=f"**Store:** amazon.com
**In-Stock Item:** {title}
**Price:** {price}",
                                    color=discord.Color.green()
                                )
                                embed.set_footer(text=f"Amazon Monitor | Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                                if img_url:
                                    embed.set_thumbnail(url=img_url)

                                await channel.send(embed=embed)
                                print(f"[{now.isoformat()}] POSTED AMAZON RESTOCK: {title}")
                                amazon_posted[url] = now
                except Exception as e:
                    print(f"Error checking Amazon URL {url}: {e}")

            await asyncio.sleep(10)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    asyncio.create_task(check_blindboxes())
    asyncio.create_task(check_popnow())
    asyncio.create_task(check_amazon())

client.run(TOKEN)