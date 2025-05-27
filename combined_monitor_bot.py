import discord
import asyncio
import aiohttp
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

TOKEN = os.getenv("TOKEN")
POP_CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # Popmart alerts
AMAZON_CHANNEL_ID = int(os.getenv("AMAZON_CHANNEL_ID"))  # Amazon alerts

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
amazon_last_alerts = {}
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
                                title="🧸 Pop Mart Restock Detected!",
                                description=f"**In-Stock Item:** [{title}]({product_url})\n**Status:** Available",
                                color=0x28a745
                            )
                            embed.set_image(url=img_url)
                            embed.set_footer(text=f"Pop Mart Monitor | Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}")
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
                set_title = data.get("data", {}).get("set_no", "Pop Now Crate")

                if any(box.get("state") == 1 for box in box_list):
                    now = datetime.now(timezone.utc)
                    if not popnow_last_alert or (now - popnow_last_alert) > timedelta(seconds=cooldown_seconds):
                        embed = discord.Embed(
                            title="📦 Pop Now Restock Detected!",
                            description=f"**Crate:** `{set_title}`\nThere are boxes available now — click below to grab one!",
                            url=POP_NOW_PAGE,
                            color=0x5bc0de
                        )
                        if img_url:
                            embed.set_image(url=img_url)
                        embed.set_footer(text=f"Pop Now Monitor | Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                        await channel.send(embed=embed)
                        popnow_last_alert = now
            except Exception as e:
                print(f"Error checking Pop Now API: {e}")
            await asyncio.sleep(10)

async def check_amazon():
    await client.wait_until_ready()
    channel = client.get_channel(AMAZON_CHANNEL_ID)
    headers = {'User-Agent': 'Mozilla/5.0'}

    async with aiohttp.ClientSession(headers=headers) as session:
        while not client.is_closed():
            for url in AMAZON_URLS:
                try:
                    async with session.get(url, timeout=10) as response:
                        html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    now = datetime.now(timezone.utc)

                    out_of_stock_text = soup.find(string=lambda t: "Currently unavailable" in t)
                    if not out_of_stock_text:
                        last_post = amazon_last_alerts.get(url, datetime.min.replace(tzinfo=timezone.utc))
                        if (now - last_post) > timedelta(seconds=cooldown_seconds):
                            title_tag = soup.find("span", {"id": "productTitle"})
                            title = title_tag.get_text(strip=True) if title_tag else "Amazon Product"
                            price_tag = soup.find("span", {"class": "a-price-whole"})
                            price = price_tag.get_text(strip=True) if price_tag else "N/A"
                            img_tag = soup.find("img", {"id": "landingImage"})
                            img_url = img_tag["src"] if img_tag else None

                            embed = discord.Embed(
                                title="🛒 Amazon Restock Detected!",
                                description=f"**In-Stock Item:** [{title}]({url})\n**Price:** ${price}",
                                color=0xff9900
                            )
                            if img_url:
                                embed.set_image(url=img_url)
                            embed.set_footer(text=f"Amazon Monitor | Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                            await channel.send(embed=embed)
                            amazon_last_alerts[url] = now
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
