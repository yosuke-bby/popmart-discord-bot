import discord
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import os
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
amazon_last_alert = {}
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
                                title="🧸 Pop Mart Restock Detected",
                                description=f"**In-Stock Item:** [{title}]({product_url})",
                                color=0xff4f8b,
                                timestamp=now
                            )
                            embed.add_field(name="Store", value="PopMart.com", inline=True)
                            embed.add_field(name="Status", value="🟢 Available", inline=True)
                            embed.add_field(name="Link", value=f"[Click to Buy]({product_url})", inline=False)
                            if img_url:
                                embed.set_thumbnail(url=img_url)

                            await channel.send(embed=embed)
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
                            title="🎁 Pop Now Labubu Restock",
                            description="Boxes are available now!",
                            color=0xff9900,
                            timestamp=now
                        )
                        embed.add_field(name="Store", value="PopMart.com", inline=True)
                        embed.add_field(name="Status", value="🟢 Available", inline=True)
                        embed.add_field(name="Link", value=f"[Open Pop Now Page]({POP_NOW_PAGE})", inline=False)
                        if img_url:
                            embed.set_thumbnail(url=img_url)

                        await channel.send(embed=embed)
                        popnow_last_alert = now

            except Exception as e:
                print(f"Error checking Pop Now API: {e}")
            await asyncio.sleep(10)

async def check_amazon():
    await client.wait_until_ready()
    channel = client.get_channel(AMAZON_CHANNEL_ID)
    global amazon_last_alert

    async with aiohttp.ClientSession() as session:
        while not client.is_closed():
            for url in AMAZON_URLS:
                try:
                    async with session.get(url, timeout=10) as resp:
                        text = await resp.text()
                        soup = BeautifulSoup(text, "html.parser")

                        title_tag = soup.select_one("#productTitle")
                        title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

                        price_tag = soup.select_one(".a-price .a-offscreen")
                        price = price_tag.get_text(strip=True) if price_tag else "Unavailable"

                        img_tag = soup.select_one("#landingImage")
                        img_url = img_tag["src"] if img_tag else None

                        is_out_of_stock = soup.find(text=lambda t: "Currently unavailable" in t)
                        in_stock = not is_out_of_stock

                        now = datetime.now(timezone.utc)
                        last_post = amazon_last_alert.get(url, datetime.min.replace(tzinfo=timezone.utc))

                        if in_stock and (now - last_post > timedelta(seconds=cooldown_seconds)):
                            embed = discord.Embed(
                                title="📦 Amazon Restock Alert",
                                description=f"**In-Stock Item:** [{title}]({url})",
                                color=0x4caf50,
                                timestamp=now
                            )
                            embed.add_field(name="Store", value="Amazon.com", inline=True)
                            embed.add_field(name="Price", value=price, inline=True)
                            embed.add_field(name="Buy", value=f"[Add to Cart]({url})", inline=False)
                            if img_url:
                                embed.set_thumbnail(url=img_url)

                            await channel.send(embed=embed)
                            amazon_last_alert[url] = now

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
