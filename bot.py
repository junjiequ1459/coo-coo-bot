import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import random
import asyncio
import aiohttp
import sqlite3
import time
import string
import io
import traceback
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

def generate_card_code() -> str:
    """Generates a random 6-character alphanumeric card code (e.g. 136hma)."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=6))

# ==========================================
# 🗄️ SQLITE DATABASE INITIALIZATION
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        user_id INTEGER NOT NULL,
        character_name TEXT NOT NULL,
        series_name TEXT NOT NULL,
        image_url TEXT NOT NULL,
        rarity TEXT NOT NULL,
        mint_number INTEGER NOT NULL,
        edition INTEGER DEFAULT 1,
        grabbed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("PRAGMA table_info(inventory)")
    columns = [column[1] for column in cursor.fetchall()]
    if "code" not in columns:
        cursor.execute("ALTER TABLE inventory ADD COLUMN code TEXT")
    if "edition" not in columns:
        cursor.execute("ALTER TABLE inventory ADD COLUMN edition INTEGER DEFAULT 1")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mints (
        character_name TEXT PRIMARY KEY,
        current_mint INTEGER NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

init_db()

def get_next_mint(character_name: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT current_mint FROM mints WHERE character_name = ?", (character_name,))
    row = cursor.fetchone()
    if row:
        next_mint = row[0] + 1
        cursor.execute("UPDATE mints SET current_mint = ? WHERE character_name = ?", (next_mint, character_name))
    else:
        next_mint = 1
        cursor.execute("INSERT INTO mints (character_name, current_mint) VALUES (?, ?)", (character_name, next_mint))
    conn.commit()
    conn.close()
    return next_mint

def save_card_to_inventory(user_id: int, code: str, character_name: str, series_name: str, image_url: str, rarity: str, mint_number: int, edition: int = 1) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO inventory (user_id, code, character_name, series_name, image_url, rarity, mint_number, edition)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, code, character_name, series_name, image_url, rarity, mint_number, edition))
    inserted_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inserted_id

def get_user_inventory(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, character_name, series_name, rarity, mint_number, edition, image_url FROM inventory WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ==========================================
# 🎨 PIL KARUTA REFERENCE-MATCHING RENDERER
# ==========================================
RARITY_COLORS = {
    "✨ Legendary": (255, 215, 0),   # Gold
    "🟣 Epic": (147, 112, 219),     # Rich Purple
    "🔷 Rare": (0, 229, 255),       # Cyan Blue
    "⚪ Common": (140, 155, 170)    # Slate Silver
}

async def fetch_image(session, url):
    try:
        async with session.get(url, timeout=8) as resp:
            if resp.status == 200:
                data = await resp.read()
                return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        print(f"Failed to fetch image {url}: {e}")
    img = Image.new("RGBA", (255, 390), (32, 34, 37, 255))
    return img

async def render_three_cards_composite(cards: list) -> io.BytesIO:
    """Renders a single horizontal 3-card composite image (820x440 px) matching Karuta's exact frame style!"""
    canvas_w, canvas_h = 820, 440
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(canvas)

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_image(session, card["image"]) for card in cards]
        raw_images = await asyncio.gather(*tasks)

    card_w, card_h = 245, 390
    padding_x = 20
    padding_y = 25

    for idx, card in enumerate(cards):
        x = padding_x + idx * (card_w + 20)
        y = padding_y
        rc = RARITY_COLORS.get(card["rarity"], (140, 155, 170))
        
        draw.rectangle([x, y, x + card_w, y + card_h], fill=(28, 30, 34, 255), outline=(60, 65, 75), width=2)
        draw.rectangle([x + 4, y + 4, x + card_w - 4, y + card_h - 4], outline=rc, width=2)
        
        raw_img = raw_images[idx]
        img_w, img_h = card_w - 14, card_h - 66
        resized_img = raw_img.resize((img_w, img_h), Image.Resampling.LANCZOS)
        canvas.paste(resized_img, (x + 7, y + 7))
        
        badge_poly = [(x + 4, y + 4), (x + 38, y + 4), (x + 44, y + 16), (x + 38, y + 34), (x + 4, y + 34)]
        draw.polygon(badge_poly, fill=(15, 16, 18), outline=rc)
        draw.text((x + 16, y + 10), str(idx + 1), fill=(255, 255, 255))
        
        box_y1 = y + card_h - 58
        box_y2 = y + card_h - 6
        draw.rectangle([x + 6, box_y1, x + card_w - 6, box_y2], fill=(12, 13, 15, 245))
        draw.line([x + 10, box_y1 + 8, x + 10, box_y2 - 8], fill=rc, width=3)
        
        draw.text((x + 20, box_y1 + 8), f"EDITION 1  |  PRINT #{card['temp_mint']}", fill=(255, 215, 0))
        draw.text((x + 20, box_y1 + 28), f"ID: {card['code']}", fill=(180, 190, 200))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

async def render_single_card(card_data: dict) -> io.BytesIO:
    """Renders a single high-quality framed Karuta card for /view-card."""
    card_w, card_h = 320, 500
    canvas = Image.new("RGBA", (card_w, card_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(canvas)

    async with aiohttp.ClientSession() as session:
        raw_img = await fetch_image(session, card_data["image_url"])

    rc = RARITY_COLORS.get(card_data["rarity"], (140, 155, 170))

    draw.rectangle([0, 0, card_w, card_h], fill=(28, 30, 34, 255), outline=(60, 65, 75), width=3)
    draw.rectangle([5, 5, card_w - 5, card_h - 5], outline=rc, width=3)

    img_w, img_h = card_w - 18, card_h - 80
    resized_img = raw_img.resize((img_w, img_h), Image.Resampling.LANCZOS)
    canvas.paste(resized_img, (9, 9))

    box_y1 = card_h - 72
    box_y2 = card_h - 8
    draw.rectangle([8, box_y1, card_w - 8, box_y2], fill=(12, 13, 15, 245))
    draw.line([14, box_y1 + 10, 14, box_y2 - 10], fill=rc, width=4)

    draw.text((26, box_y1 + 10), f"EDITION {card_data.get('edition', 1)}  |  PRINT #{card_data['mint_number']}", fill=(255, 215, 0))
    draw.text((26, box_y1 + 34), f"ID: {card_data['code'].upper()}", fill=(240, 240, 240))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ==========================================
# 🌐 ANILIST PUBLIC API INTEGRATION
# ==========================================
ANILIST_URL = "https://graphql.anilist.co"

ANILIST_QUERY = """query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    characters(sort: FAVOURITES_DESC) {
      id
      name {
        full
      }
      image {
        large
      }
      favourites
      media(perPage: 1) {
        nodes {
          title {
            english
            romaji
          }
        }
      }
    }
  }
}"""

async def fetch_random_anilist_cards(count: int = 3):
    """Fetches random popular anime characters from AniList API."""
    random_page = random.randint(1, 35)
    variables = {"page": random_page, "perPage": 25}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(ANILIST_URL, json={"query": ANILIST_QUERY, "variables": variables}, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    char_list = data["data"]["Page"]["characters"]
                    selected = random.sample(char_list, min(count, len(char_list)))
                    
                    cards = []
                    for char in selected:
                        char_name = char["name"]["full"]
                        img_url = char["image"]["large"]
                        favs = char.get("favourites", 0)
                        
                        media_nodes = char.get("media", {}).get("nodes", [])
                        if media_nodes and media_nodes[0].get("title"):
                            series = media_nodes[0]["title"].get("english") or media_nodes[0]["title"].get("romaji") or "Anime Series"
                        else:
                            series = "Anime Series"
                            
                        if favs >= 15000:
                            rarity = "✨ Legendary"
                        elif favs >= 5000:
                            rarity = "🟣 Epic"
                        elif favs >= 1500:
                            rarity = "🔷 Rare"
                        else:
                            rarity = "⚪ Common"
                            
                        temp_mint = get_next_mint(char_name)
                        cards.append({
                            "code": generate_card_code(),
                            "name": char_name,
                            "series": series,
                            "image": img_url,
                            "rarity": rarity,
                            "temp_mint": temp_mint,
                            "edition": 1
                        })
                    return cards
                else:
                    print(f"AniList API Status Error: {resp.status}")
                    return None
        except Exception as e:
            print(f"AniList Fetch Exception: {e}")
            return None

# ==========================================
# 🎨 COLOR ROLES CONFIGURATION
# ==========================================
COLOR_ROLES = [
    {"name": "Cherry Pink", "emoji": "🩷", "hex": 0xFFB6C1},
    {"name": "Lavender", "emoji": "💜", "hex": 0x9370DB},
    {"name": "Sunset Red", "emoji": "🔴", "hex": 0xE60023},
    {"name": "Mint Green", "emoji": "💚", "hex": 0x98FF98},
    {"name": "Sky Blue", "emoji": "🩵", "hex": 0x87CEEB},
    {"name": "Lemon Yellow", "emoji": "💛", "hex": 0xFFFACD},
    {"name": "Peach Coral", "emoji": "🧡", "hex": 0xFF7F50},
    {"name": "Royal Blue", "emoji": "💙", "hex": 0x007AFF},
    {"name": "Pure White", "emoji": "🤍", "hex": 0xFFFFFF},
    {"name": "Midnight", "emoji": "🖤", "hex": 0x36393F},
]

PIGEON_MESSAGES = [
    "Coo coo! 🍞 Don't let a bad sketch ruin your day. Even a dropped bagel on 5th Ave gets a second chance!",
    "Coo coo! 🎨 You don't need perfection, you just need to start. Look at me — I can't read the room, but I still show up!",
    "Coo coo! 🍟 If someone tells you your goals are too big, tell them you're just aerodynamically blessed like me!",
    "Coo coo! 🗽 Life is tough, but so is NYC sidewalk pizza. Keep chewing and keep creating!",
    "Coo coo! 🌾 Take a break, stretch your wrist, and drink water. You can't draw masterpieces on an empty stomach!",
    "Coo coo! 👔 Wear your bowtie with confidence, even when you're just hunting for breadcrumbs!",
    "Coo coo! ✨ Art block is temporary, but your talent is forever. Go make something cool!",
    "Coo coo! 🥯 They said I couldn't fly over the park bench because I was too fat. I waddled instead. Adapt and conquer!",
    "Coo coo! 💅 Never be afraid to third-wheel your own success!",
    "Coo coo! 🎨 Yuki told me every artist starts with a rough draft. Mine was a pretzel stain on the sidewalk!",
    "Coo coo! 🌟 Ratan told me to reach for the stars. I reached for a French fry instead, but the energy is the same!",
    "Coo coo! 🍕 Keep pushing forward! Every line you draw brings you closer to your dream!"
]

# ==========================================
# 🎴 CARD DROP BUTTON UI
# ==========================================
class CardGrabButton(discord.ui.Button):
    def __init__(self, index: int, card_info: dict):
        super().__init__(
            label=f"Grab Card {index + 1}",
            emoji=["1️⃣", "2️⃣", "3️⃣"][index],
            style=discord.ButtonStyle.primary,
            custom_id=f"coocoo_grab_{index}_{random.randint(10000, 99999)}"
        )
        self.index = index
        self.card_info = card_info

    async def callback(self, interaction: discord.Interaction):
        view: CardDropView = self.view
        if view.claimed:
            await interaction.response.send_message("Coo coo! ⚠️ This drop has already been claimed!", ephemeral=True)
            return

        view.claimed = True
        
        for child in view.children:
            child.disabled = True
            if child == self:
                child.label = f"Claimed by {interaction.user.display_name}"
                child.style = discord.ButtonStyle.success

        save_card_to_inventory(
            user_id=interaction.user.id,
            code=self.card_info["code"],
            character_name=self.card_info["name"],
            series_name=self.card_info["series"],
            image_url=self.card_info["image"],
            rarity=self.card_info["rarity"],
            mint_number=self.card_info["temp_mint"],
            edition=1
        )

        embed = discord.Embed(
            title=f"🎉 Claimed: {self.card_info['name']}",
            description=(
                f"👤 **Claimed by:** {interaction.user.mention}\n"
                f"📺 **Series:** {self.card_info['series']}\n"
                f"🆔 **Card ID:** `{self.card_info['code']}`"
            ),
            color=discord.Color.gold()
        )

        await interaction.response.edit_message(embeds=[embed], view=view)
        await interaction.followup.send(
            f"🎉 {interaction.user.mention} grabbed **{self.card_info['name']}** (**Edition 1 • Print #{self.card_info['temp_mint']}**)! `Card ID: {self.card_info['code']}`"
        )

class CardDropView(discord.ui.View):
    def __init__(self, cards: list):
        super().__init__(timeout=180)
        self.cards = cards
        self.claimed = False
        for idx, card in enumerate(cards):
            self.add_item(CardGrabButton(idx, card))

class ColorButton(discord.ui.Button):
    def __init__(self, color_info):
        super().__init__(
            label=f"{color_info['emoji']} {color_info['name']}",
            style=discord.ButtonStyle.secondary,
            custom_id=f"coocoo_color_{color_info['name'].lower().replace(' ', '_')}"
        )
        self.color_info = color_info

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        target_role_name = self.color_info["name"]
        target_role = discord.utils.get(guild.roles, name=target_role_name)

        if not target_role:
            try:
                target_role = await guild.create_role(
                    name=target_role_name,
                    color=discord.Color(self.color_info["hex"]),
                    reason="Coo Coo Color Role Auto-Creation"
                )
            except discord.Forbidden:
                await interaction.followup.send("Coo coo! ⚠️ I don't have 'Manage Roles' permission!", ephemeral=True)
                return
        else:
            try:
                await target_role.edit(color=discord.Color(self.color_info["hex"]))
            except Exception:
                pass

        color_role_names = [c["name"] for c in COLOR_ROLES]
        roles_to_remove = [r for r in member.roles if r.name in color_role_names and r.name != target_role_name]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)

        if target_role not in member.roles:
            await member.add_roles(target_role)
            await interaction.followup.send(
                f"Coo coo! 🐦 {self.color_info['emoji']} Your name color is now **{target_role_name}**!",
                ephemeral=True
            )
        else:
            await interaction.followup.send(f"Coo coo! 🐦 You already have **{target_role_name}**!", ephemeral=True)

class ColorPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for color in COLOR_ROLES:
            self.add_item(ColorButton(color))

# ==========================================
# 🤖 BOT DISCORD CLIENT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🐦 Coo Coo is ONLINE as {bot.user.name} ({bot.user.id})!")
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} Slash Commands to guild '{guild.name}' ({guild.id})!")
        except Exception as e:
            print(f"Guild sync error for {guild.name}: {e}")

    bot.add_view(ColorPickerView())

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general") or discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        embed = discord.Embed(
            title=f"🐦 Coo Coo Welcomes {member.display_name}!",
            description=(
                f"Coo coo! 🍞 Welcome to the nest, {member.mention}!\n\n"
                f"I'm Coo Coo — New York's fattest pigeon and Yuki's friend! "
                f"Head over to `#get-roles` to pick a name color!\n\n"
                f"Here, take a fresh pretzel crust 🥨!"
            ),
            color=discord.Color.from_rgb(255, 182, 193)
        )
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        await channel.send(embed=embed)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"❌ Slash command error: {error}")

# ==========================================
# 🎴 ANILIST CARD DROP & INVENTORY COMMANDS
# ==========================================

async def execute_card_drop(ctx_or_interaction, user):
    """Core logic to fetch cards and render a single horizontal 3-card side-by-side image!"""
    cards = await fetch_random_anilist_cards(3)
    if not cards:
        msg = "Coo coo! ⚠️ Couldn't reach AniList. Please try again in a moment!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    buf = await render_three_cards_composite(cards)
    file = discord.File(fp=buf, filename="drop.png")

    embed = discord.Embed(
        title=f"🎴 {user.display_name}'s Card Drop!",
        description=(
            f"1️⃣ **{cards[0]['name']}** · *{cards[0]['series']}*\n"
            f"2️⃣ **{cards[1]['name']}** · *{cards[1]['series']}*\n"
            f"3️⃣ **{cards[2]['name']}** · *{cards[2]['series']}*\n\n"
            f"Click a button below to grab a card!"
        ),
        color=discord.Color.gold()
    )
    embed.set_image(url="attachment://drop.png")
    embed.set_footer(text="Coo Coo Card Engine • Side-By-Side View")

    view = CardDropView(cards)

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.followup.send(embed=embed, file=file, view=view)
    else:
        await ctx_or_interaction.send(embed=embed, file=file, view=view)

@bot.tree.command(name="drop", description="Drops 3 random Anime Cards from AniList!")
async def drop_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await execute_card_drop(interaction, interaction.user)

@bot.command(name="drop")
async def drop_prefix(ctx):
    await execute_card_drop(ctx, ctx.author)

@bot.tree.command(name="inventory", description="View your collected Anime Cards")
async def inventory_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    rows = get_user_inventory(interaction.user.id)
    if not rows:
        await interaction.followup.send("Coo coo! 🎴 You haven't grabbed any cards yet! Type `/drop` to start collecting!")
        return

    embed = discord.Embed(
        title=f"🎴 {interaction.user.display_name}'s Card Collection",
        description=f"Total Cards Collected: **{len(rows)}**",
        color=discord.Color.purple()
    )

    for row in rows[:10]:
        card_id, code, char_name, series, rarity, mint_num, edition, img_url = row
        code_str = code if code else f"c{card_id:04d}"
        ed_val = edition if edition else 1
        embed.add_field(
            name=f"🆔 Card ID: `{code_str}` • {char_name}",
            value=f"Edition {ed_val} • Print #{mint_num} | 📺 *{series}* | {rarity}",
            inline=False
        )

    if len(rows) > 10:
        embed.set_footer(text=f"Showing 10 of {len(rows)} cards. Type /view-card to see full card artwork!")
    else:
        embed.set_footer(text="Type /view-card to see full card artwork!")

    await interaction.followup.send(embed=embed)

@bot.command(name="inventory")
async def inventory_prefix(ctx):
    rows = get_user_inventory(ctx.author.id)
    if not rows:
        await ctx.send("Coo coo! 🎴 You haven't grabbed any cards yet! Type `!drop` to start collecting!")
        return

    embed = discord.Embed(
        title=f"🎴 {ctx.author.display_name}'s Card Collection",
        description=f"Total Cards Collected: **{len(rows)}**",
        color=discord.Color.purple()
    )

    for row in rows[:10]:
        card_id, code, char_name, series, rarity, mint_num, edition, img_url = row
        code_str = code if code else f"c{card_id:04d}"
        ed_val = edition if edition else 1
        embed.add_field(
            name=f"🆔 Card ID: `{code_str}` • {char_name}",
            value=f"Edition {ed_val} • Print #{mint_num} | 📺 *{series}* | {rarity}",
            inline=False
        )

    await ctx.send(embed=embed)

async def process_view_card(ctx_or_interaction, card_code_query: str = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not card_code_query:
        # Fetch the user's most recently grabbed card!
        cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, grabbed_at FROM inventory WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user.id,))
    else:
        query_str = card_code_query.lower().strip()
        cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, grabbed_at FROM inventory WHERE code = ? OR id = ?", (query_str, query_str))
    
    row = cursor.fetchone()
    conn.close()

    if not row:
        if not card_code_query:
            msg = "Coo coo! ⚠️ You don't have any cards in your inventory yet! Type `/drop` to grab your first card!"
        else:
            msg = f"Coo coo! ⚠️ Card ID `{card_code_query}` not found in database!"
            
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    cid, code, uid, char_name, series, rarity, mint_num, edition, img_url, grabbed_at = row
    owner = bot.get_user(uid)
    owner_name = owner.display_name if owner else f"User {uid}"
    ed_val = edition if edition else 1
    code_str = code if code else f"c{cid:04d}"

    card_data = {
        "id": cid,
        "code": code_str,
        "character_name": char_name,
        "series_name": series,
        "rarity": rarity,
        "mint_number": mint_num,
        "edition": ed_val,
        "image_url": img_url
    }

    buf = await render_single_card(card_data)
    file = discord.File(fp=buf, filename="card.png")

    embed = discord.Embed(
        title=f"🆔 Card ID: {code_str} • {char_name}",
        description=(
            f"📺 **Series:** {series}\n"
            f"👤 **Owner:** {owner_name}\n"
            f"📅 **Grabbed:** {grabbed_at}"
        ),
        color=discord.Color.magenta()
    )
    embed.set_image(url="attachment://card.png")
    embed.set_footer(text=f"Coo Coo Card Vault • Card ID: {code_str}")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.followup.send(embed=embed, file=file)
    else:
        await ctx_or_interaction.send(embed=embed, file=file)

@bot.tree.command(name="view-card", description="View full details and artwork of a card (Defaults to your latest card)")
async def view_card_slash(interaction: discord.Interaction, card_code: str = None):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_view_card(interaction, card_code)

@bot.command(name="v")
async def view_card_prefix_v(ctx, card_code: str = None):
    await process_view_card(ctx, card_code)

@bot.command(name="view")
async def view_card_prefix_view(ctx, card_code: str = None):
    await process_view_card(ctx, card_code)

# ==========================================
# 🎨 OTHER COMMANDS
# ==========================================

@bot.command(name="setup-colors")
async def setup_colors_prefix(ctx):
    embed = discord.Embed(
        title="🐦 Coo Coo's Color Nest",
        description="Pick a color below to customize your username color in the server!",
        color=discord.Color.from_rgb(138, 158, 167)
    )
    embed.set_footer(text="Coo Coo • Select your favorite vibe!")
    await ctx.send(embed=embed, view=ColorPickerView())

@bot.tree.command(name="setup-colors", description="Spawns the Coo Coo Color Selection Buttons")
async def setup_colors_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    embed = discord.Embed(
        title="🐦 Coo Coo's Color Nest",
        description="Pick a color below to customize your username color in the server!",
        color=discord.Color.from_rgb(138, 158, 167)
    )
    embed.set_footer(text="Coo Coo • Select your favorite vibe!")
    await interaction.followup.send(embed=embed, view=ColorPickerView())

@bot.command(name="coo")
async def coo_prefix(ctx):
    msg = random.choice(PIGEON_MESSAGES)
    await ctx.send(f"🐦 **Coo Coo**: {msg}")

@bot.tree.command(name="coo", description="Coo Coo shares motivational pigeon wisdom!")
async def coo_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    msg = random.choice(PIGEON_MESSAGES)
    await interaction.followup.send(f"🐦 **Coo Coo**: {msg}")

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ Error: Please put your Discord Bot Token in the .env file!")
    else:
        bot.run(TOKEN)
