import discord
import asyncio
import aiohttp
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# ─── Configuration ─────────────────────────────────────────────────────────────
TOKEN             = os.getenv("TOKEN")
POP_CHANNEL_ID    = int(os.getenv("CHANNEL_ID"))        # Channel for Pop Mart alerts
AMAZON_CHANNEL_ID = int(os.getenv("AMAZON_CHANNEL_ID")) # Channel for Amazon alerts

BLIND_BOX_URL = "https://prod-na-api.popmart.com/shop/v3/shop/productOnCollection"
POP_NOW_URL   = "https://prod-na-api.popmart.com/shop/v1/box/box_set/extract"
POP_NOW_PAGE  = "https://www.popmart.com/pages/popnow"

AMAZON_URLS = [
    "https://www.amazon.com/POP-MART-Big-into-Energy/dp/B0DT44TSM2?th=1",
    "https://www.amazon.com/POP-MART-Big-into-Energy/dp/B0DT41V371?ref_=ast_sto_dp&th=1",
    "https://www.amazon.com/POP-MART-Monsters-Collectible-Accessories/dp/B0CL6PLZ3Y?th=1"
]

COOLDOWN_SECONDS = 60  # seconds between alerts for the same item

# ─── Bot Setup ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
client  = discord.Client(intents=intents)

blindbox_posted    = {}  # title -> last alert time
popnow_last_alert  = None
amazon_last_alerts = {}  # url   -> last alert time

# ─── Pop Mart Blind Boxes ───────────────────────────────────────────────────────
async def check_blindboxes():
    await client.wait_until_ready()
    channel = client.get_channel(POP_CHANNEL_ID)
    async with aiohttp.ClientSession() as session:
        while not client.is_closed():
            try:
                resp = await session.get(BLIND_BOX_URL, timeout=10)
                data = await resp.json()
                items = data.get("data", {}).get("items", [])
                now   = datetime.now(timezone.utc)

                for item in items:
                    title     = item.get("name", "No Title")
                    available = (item.get("status") == "AVAILABLE")
                    url       = f"https://popmart.com/product/{item.get('spuCode','')}"
                    img       = item.get("cover","")

                    if available:
                        last = blindbox_posted.get(title, datetime.min.replace(tzinfo=timezone.utc))
                        if (now - last).total_seconds() > COOLDOWN_SECONDS:
                            embed = discord.Embed(
                                title="🧸 Pop Mart Blind Box Restock!",
                                description=f"**Item:** [{title}]({url})\n**Status:** Available now!",
                                color=0x28a745,
                                timestamp=now
                            )
                            if img:
                                embed.set_thumbnail(url=img)
                            embed.set_footer(text="Pop Mart Monitor")
                            await channel.send(embed=embed)
                            blindbox_posted[title] = now

            except Exception as e:
                print("Blind Box check error:", e)

            await asyncio.sleep(10)

# ─── Pop Mart Pop Now ───────────────────────────────────────────────────────────
async def check_popnow():
    await client.wait_until_ready()
    channel = client.get_channel(POP_CHANNEL_ID)
    global popnow_last_alert

    async with aiohttp.ClientSession() as session:
        while not client.is_closed():
            try:
                resp = await session.post(POP_NOW_URL, timeout=10)
                data = await resp.json()
                box_list = data.get("data", {}).get("box_list", [])
                img      = data.get("data", {}).get("set_main_pic","")
                set_no   = data.get("data", {}).get("set_no","Pop Now Crate")
                now      = datetime.now(timezone.utc)

                # DEBUG: Log what the API returns
                print(f"[DEBUG PopNow] {len(box_list)} boxes → {box_list}")

                if box_list:
                    # Send one alert per restock event
                    if not popnow_last_alert or (now - popnow_last_alert).total_seconds() > COOLDOWN_SECONDS:
                        embed = discord.Embed(
                            title="📦 Pop Now Crate Restocked!",
                            description=f"**Crate:** `{set_no}`\nBoxes are live — go grab one!",
                            url=POP_NOW_PAGE,
                            color=0x5bc0de,
                            timestamp=now
                        )
                        if img:
                            embed.set_image(url=img)
                        embed.set_footer(text="Pop Now Monitor")
                        await channel.send(embed=embed)
                        popnow_last_alert = now

            except Exception as e:
                print("Pop Now check error:", e)

            await asyncio.sleep(10)

# ─── Amazon Restock ─────────────────────────────────────────────────────────────
async def check_amazon():
    await client.wait_until_ready()
    channel = client.get_channel(AMAZON_CHANNEL_ID)
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession(headers=headers) as session:
        while not client.is_closed():
            for url in AMAZON_URLS:
                try:
                    resp = await session.get(url, timeout=10)
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    now  = datetime.now(timezone.utc)

                    # Only trigger when the actual "In Stock." text appears
                    avail_block = soup.select_one("#availability")
                    avail_text  = avail_block.get_text(strip=True).lower() if avail_block else ""
                    if "in stock" in avail_text:
                        title_tag = soup.select_one("#productTitle")
                        price_tag = soup.select_one(".a-price .a-offscreen")
                        title      = title_tag.get_text(strip=True) if title_tag else None
                        price      = price_tag.get_text(strip=True) if price_tag else None

                        if title and price:
                            last = amazon_last_alerts.get(url, datetime.min.replace(tzinfo=timezone.utc))
                            if (now - last).total_seconds() > COOLDOWN_SECONDS:
                                embed = discord.Embed(
                                    title="🛒 Amazon Restock Detected!",
                                    description=f"**Item:** [{title}]({url})\n**Price:** {price}",
                                    color=0xff9900,
                                    timestamp=now
                                )
                                img_tag = soup.select_one("#landingImage")
                                if img_tag and img_tag.get("src"):
                                    embed.set_image(url=img_tag["src"])
                                embed.set_footer(text="Amazon Monitor")
                                await channel.send(embed=embed)
                                amazon_last_alerts[url] = now

                except Exception as e:
                    print(f"Amazon check error for {url}:", e)

            await asyncio.sleep(10)

# ─── Bot Events & Run ───────────────────────────────────────────────────────────
@client.event
async def on_ready():
    print("✅ Logged in as", client.user)
    asyncio.create_task(check_blindboxes())
    asyncio.create_task(check_popnow())
    asyncio.create_task(check_amazon())

client.run(TOKEN)
