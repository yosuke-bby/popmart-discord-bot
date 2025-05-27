import discord
import asyncio
import aiohttp
import os
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # Pop Mart alerts
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
popnow_in_stock = False
amazon_last_alert = {}
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
                    price = product.get("price", {}).get("unitPrice", "N/A")

                    if available:
                        last_post = blindbox_posted.get(title, datetime.min.replace(tzinfo=timezone.utc))
                        if (now - last_post) > timedelta(seconds=cooldown_seconds):
                            embed = discord.Embed(
                                title="🎉 Blind Box Restock Detected!",
                                description=f"**Status:** In Stock\n**Title:** {title}\n**Price:** ¥{price}\n[Buy Now]({product_url})",
                                color=discord.Color.green()
                            )
                            if img_url:
                                embed.set_thumbnail(url=img_url)
                            await channel.send(embed=embed)
                            blindbox_posted[title] = now

            except Exception as e:
                print(f"Error checking Blind Box API: {e}")
            await asyncio.sleep(10)

async def check_popnow():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    global popnow_in_stock

    async with aiohttp.ClientSession() as session:
        while not client.is_closed():
            try:
                async with session.post(POP_NOW_URL, timeout=10) as response:
                    data = await response.json()

                box_list = data.get("data", {}).get("box_list", [])
                img_url = data.get("data", {}).get("set_main_pic", "")
                available = any(box.get("state") == 1 for box in box_list)

                if available and not popnow_in_stock:
                    embed = discord.Embed(
                        title="🚨 Pop Now Labubu Crate Restocked!",
                        description=f"Boxes are available to open!\n[Go to Pop Now]({POP_NOW_PAGE})",
                        color=discord.Color.orange()
                    )
                    if img_url:
                        embed.set_thumbnail(url=img_url)
                    await channel.send(embed=embed)
                    print("[Pop Now] Restock alert sent.")
                    popnow_in_stock = True

                elif not available and popnow_in_stock:
                    print("[Pop Now] Stock is empty again.")
                    popnow_in_stock = False

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
                    async with session.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as response:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")

                    is_out_of_stock = soup.find(string=lambda t: "Currently unavailable" in t)
                    title_tag = soup.find("span", id="productTitle")
                    price_tag = soup.find("span", class_="a-price-whole")
                    asin = url.split("/dp/")[1].split("/")[0]

                    if not is_out_of_stock and title_tag:
                        now = datetime.now(timezone.utc)
                        title = title_tag.get_text(strip=True)
                        price = price_tag.get_text(strip=True) if price_tag else "N/A"

                        last_post = amazon_last_alert.get(asin, datetime.min.replace(tzinfo=timezone.utc))
                        if (now - last_post) > timedelta(seconds=cooldown_seconds):
                            embed = discord.Embed(
                                title="🛒 Amazon Restock Detected!",
                                description=f"**Status:** In Stock\n**Title:** {title}\n**ASIN:** {asin}\n**Price:** ${price}\n[Add to Cart]({url})",
                                color=discord.Color.blue()
                            )
                            image_tag = soup.find("img", id="landingImage")
                            if image_tag:
                                embed.set_thumbnail(url=image_tag["src"])

                            await channel.send(embed=embed)
                            amazon_last_alert[asin] = now

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