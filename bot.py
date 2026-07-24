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

def get_card_by_code_and_owner(code: str, user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition FROM inventory WHERE (code = ? OR id = ?) AND user_id = ?", (code.lower().strip(), code.strip(), user_id))
    row = cursor.fetchone()
    conn.close()
    return row

def transfer_cards_between_users(user1_id: int, user1_codes: list, user2_id: int, user2_codes: list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        for code in user1_codes:
            cursor.execute("UPDATE inventory SET user_id = ? WHERE code = ?", (user2_id, code))
        for code in user2_codes:
            cursor.execute("UPDATE inventory SET user_id = ? WHERE code = ?", (user1_id, code))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error transferring cards: {e}")
        conn.rollback()
        conn.close()
        return False

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
    img = Image.new("RGBA", (260, 400), (32, 34, 37, 255))
    return img

async def render_three_cards_composite(cards: list) -> io.BytesIO:
    """Renders a single horizontal 3-card composite image (850x450 px) matching Karuta's exact frame style!"""
    canvas_w, canvas_h = 850, 450
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(canvas)

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_image(session, card["image"]) for card in cards]
        raw_images = await asyncio.gather(*tasks)

    card_w, card_h = 255, 400
    padding_x = 20
    padding_y = 25

    for idx, card in enumerate(cards):
        x = padding_x + idx * (card_w + 20)
        y = padding_y
        rc = RARITY_COLORS.get(card["rarity"], (140, 155, 170))
        
        # 1. Outer Dark Frame & Inner Inset Line
        draw.rectangle([x, y, x + card_w, y + card_h], fill=(28, 30, 34, 255), outline=(60, 65, 75), width=2)
        draw.rectangle([x + 4, y + 4, x + card_w - 4, y + card_h - 4], outline=rc, width=2)
        
        # 2. Paste Resized Image
        raw_img = raw_images[idx]
        img_w, img_h = card_w - 14, card_h - 68
        resized_img = raw_img.resize((img_w, img_h), Image.Resampling.LANCZOS)
        canvas.paste(resized_img, (x + 7, y + 7))
        
        # 3. Top-Left Badge
        badge_poly = [(x + 4, y + 4), (x + 38, y + 4), (x + 44, y + 16), (x + 38, y + 34), (x + 4, y + 34)]
        draw.polygon(badge_poly, fill=(15, 16, 18), outline=rc)
        draw.text((x + 16, y + 10), str(idx + 1), fill=(255, 255, 255))
        
        # 4. Bottom Info Box
        box_y1 = y + card_h - 60
        box_y2 = y + card_h - 6
        draw.rectangle([x + 6, box_y1, x + card_w - 6, box_y2], fill=(12, 13, 15, 245))
        draw.line([x + 10, box_y1 + 8, x + 10, box_y2 - 8], fill=rc, width=3)
        
        # Left Text (Short Edition & ID)
        draw.text((x + 18, box_y1 + 6), f"ED 1 | #{card['temp_mint']}", fill=(255, 215, 0))
        draw.text((x + 18, box_y1 + 30), f"ID: {card['code']}", fill=(180, 190, 200))

        char_disp = card['name'][:24]
        series_disp = card['series'][:24]
        draw.text((x + card_w - 14, box_y1 + 6), char_disp, fill=(255, 255, 255), anchor="ra")
        draw.text((x + card_w - 14, box_y1 + 30), series_disp, fill=(150, 165, 180), anchor="ra")

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

async def render_single_card(card_data: dict) -> io.BytesIO:
    """Renders a single high-quality framed Karuta card for /card."""
    card_w, card_h = 340, 520
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

    draw.text((24, box_y1 + 10), f"ED {card_data.get('edition', 1)} | #{card_data['mint_number']}", fill=(255, 215, 0))
    draw.text((24, box_y1 + 34), f"ID: {card_data['code'].upper()}", fill=(240, 240, 240))

    char_disp = card_data['character_name'][:26]
    series_disp = card_data['series_name'][:26]
    draw.text((card_w - 18, box_y1 + 10), char_disp, fill=(255, 255, 255), anchor="ra")
    draw.text((card_w - 18, box_y1 + 34), series_disp, fill=(160, 175, 190), anchor="ra")

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

async def fetch_single_card_from_page(session, page: int):
    variables = {"page": page, "perPage": 25}
    try:
        async with session.post(ANILIST_URL, json={"query": ANILIST_QUERY, "variables": variables}, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                char_list = data["data"]["Page"]["characters"]
                if char_list:
                    return random.choice(char_list)
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
    return None

async def fetch_random_anilist_cards(count: int = 3):
    """Fetches 3 individual random characters from varied AniList popularity tiers."""
    pages_to_sample = [
        random.randint(1, 4),    # Top Tier / Legendary / Epic candidates
        random.randint(5, 18),   # Mid Tier / Epic / Rare candidates
        random.randint(19, 50)   # Lower Tier / Rare / Common candidates
    ]
    random.shuffle(pages_to_sample)
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_single_card_from_page(session, p) for p in pages_to_sample[:count]]
        results = await asyncio.gather(*tasks)

    cards = []
    for char in results:
        if not char:
            continue
        char_name = char["name"]["full"]
        img_url = char["image"]["large"]
        favs = char.get("favourites", 0)
        
        media_nodes = char.get("media", {}).get("nodes", [])
        if media_nodes and media_nodes[0].get("title"):
            series = media_nodes[0]["title"].get("english") or media_nodes[0]["title"].get("romaji") or "Anime Series"
        else:
            series = "Anime Series"
            
        if favs >= 12000:
            rarity = "✨ Legendary"
        elif favs >= 4000:
            rarity = "🟣 Epic"
        elif favs >= 1000:
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

        elapsed = time.time() - view.drop_time
        if elapsed < 10.0 and interaction.user.id != view.dropper_id:
            remaining = int(10.0 - elapsed) + 1
            await interaction.response.send_message(
                f"Coo coo! ⏳ <@{view.dropper_id}> has **10 seconds of drop priority**! ({remaining}s remaining)",
                ephemeral=True
            )
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
    def __init__(self, cards: list, dropper_id: int):
        super().__init__(timeout=180)
        self.cards = cards
        self.dropper_id = dropper_id
        self.drop_time = time.time()
        self.claimed = False
        self.message = None
        for idx, card in enumerate(cards):
            self.add_item(CardGrabButton(idx, card))

    async def on_timeout(self):
        if not self.claimed:
            for child in self.children:
                child.disabled = True
                child.label = "Drop Expired"
                child.style = discord.ButtonStyle.secondary
            if self.message:
                try:
                    await self.message.edit(view=self)
                except Exception:
                    pass

# ==========================================
# 🔄 KARUTA-STYLE TRADING ENGINE
# ==========================================
ACTIVE_TRADES = {}  # {channel_id: TradeSession}

class AddCardModal(discord.ui.Modal, title="Add Card to Trade"):
    card_code_input = discord.ui.TextInput(
        label="Card ID",
        placeholder="Enter 6-character Card ID (e.g. 136hma)",
        min_length=3,
        max_length=10,
        required=True
    )

    def __init__(self, trade_session):
        super().__init__()
        self.trade_session = trade_session

    async def on_submit(self, interaction: discord.Interaction):
        await self.trade_session.add_card(interaction, self.card_code_input.value.strip())

class RemoveCardModal(discord.ui.Modal, title="Remove Card from Trade"):
    card_code_input = discord.ui.TextInput(
        label="Card ID to Remove",
        placeholder="Enter Card ID currently in trade (e.g. 136hma)",
        min_length=3,
        max_length=10,
        required=True
    )

    def __init__(self, trade_session):
        super().__init__()
        self.trade_session = trade_session

    async def on_submit(self, interaction: discord.Interaction):
        await self.trade_session.remove_card(interaction, self.card_code_input.value.strip())

class TradeView(discord.ui.View):
    def __init__(self, trade_session):
        super().__init__(timeout=300)
        self.trade_session = trade_session

    @discord.ui.button(label="Offer Card", style=discord.ButtonStyle.primary, emoji="➕")
    async def offer_card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.trade_session.p1.id, self.trade_session.p2.id]:
            await interaction.response.send_message("Coo coo! ⚠️ You are not part of this trade session!", ephemeral=True)
            return
        await interaction.response.send_modal(AddCardModal(self.trade_session))

    @discord.ui.button(label="Remove Card", style=discord.ButtonStyle.secondary, emoji="➖")
    async def remove_card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.trade_session.p1.id, self.trade_session.p2.id]:
            await interaction.response.send_message("Coo coo! ⚠️ You are not part of this trade session!", ephemeral=True)
            return
        await interaction.response.send_modal(RemoveCardModal(self.trade_session))

    @discord.ui.button(label="Confirm Trade", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.trade_session.p1.id, self.trade_session.p2.id]:
            await interaction.response.send_message("Coo coo! ⚠️ You are not part of this trade session!", ephemeral=True)
            return
        await self.trade_session.confirm_user(interaction, interaction.user.id)

    @discord.ui.button(label="Cancel Trade", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.trade_session.p1.id, self.trade_session.p2.id]:
            await interaction.response.send_message("Coo coo! ⚠️ You are not part of this trade session!", ephemeral=True)
            return
        await self.trade_session.cancel_trade(interaction, interaction.user)

class TradeSession:
    def __init__(self, channel, p1: discord.User, p2: discord.User):
        self.channel = channel
        self.p1 = p1
        self.p2 = p2
        self.p1_cards = []
        self.p2_cards = []
        self.p1_confirmed = False
        self.p2_confirmed = False
        self.message = None
        self.view = TradeView(self)

    def render_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🔄 Active Trade Session",
            description=f"Trading between {self.p1.mention} and {self.p2.mention}",
            color=discord.Color.blue()
        )

        p1_text = ""
        if self.p1_cards:
            for c in self.p1_cards:
                p1_text += f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})\n"
        else:
            p1_text = "*No cards offered yet*"
        p1_status = "✅ **CONFIRMED**" if self.p1_confirmed else "⏳ *Waiting...*"

        p2_text = ""
        if self.p2_cards:
            for c in self.p2_cards:
                p2_text += f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})\n"
        else:
            p2_text = "*No cards offered yet*"
        p2_status = "✅ **CONFIRMED**" if self.p2_confirmed else "⏳ *Waiting...*"

        embed.add_field(
            name=f"👤 {self.p1.display_name}'s Offer ({p1_status})",
            value=p1_text,
            inline=True
        )
        embed.add_field(
            name=f"👤 {self.p2.display_name}'s Offer ({p2_status})",
            value=p2_text,
            inline=True
        )
        embed.set_footer(text="Use buttons below or type !ta <code_or_id> / !tr <code_or_id> in chat!")
        return embed

    async def update_message(self, interaction=None):
        embed = self.render_embed()
        if interaction:
            try:
                await interaction.response.edit_message(embed=embed, view=self.view)
                return
            except Exception:
                pass
        if self.message:
            try:
                await self.message.edit(embed=embed, view=self.view)
            except Exception:
                pass

    async def add_card(self, interaction_or_ctx, code_str: str):
        is_p1 = (interaction_or_ctx.user.id if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.author.id) == self.p1.id
        user = self.p1 if is_p1 else self.p2
        target_list = self.p1_cards if is_p1 else self.p2_cards

        card_row = get_card_by_code_and_owner(code_str, user.id)
        if not card_row:
            msg = f"Coo coo! ⚠️ Card `{code_str}` is not in your inventory!"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await interaction_or_ctx.response.send_message(msg, ephemeral=True)
            else:
                await interaction_or_ctx.send(msg)
            return

        cid, code, uid, char_name, series, rarity, mint_num, edition = card_row
        card_code = code if code else f"c{cid:04d}"

        if any(c["code"] == card_code for c in target_list):
            msg = f"Coo coo! ⚠️ Card `{card_code}` is already in the trade!"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await interaction_or_ctx.response.send_message(msg, ephemeral=True)
            else:
                await interaction_or_ctx.send(msg)
            return

        target_list.append({
            "id": cid,
            "code": card_code,
            "character_name": char_name,
            "series_name": series,
            "rarity": rarity
        })

        self.p1_confirmed = False
        self.p2_confirmed = False

        if isinstance(interaction_or_ctx, discord.Interaction):
            await self.update_message(interaction_or_ctx)
        else:
            await self.update_message()

    async def remove_card(self, interaction_or_ctx, code_str: str):
        is_p1 = (interaction_or_ctx.user.id if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.author.id) == self.p1.id
        target_list = self.p1_cards if is_p1 else self.p2_cards

        code_clean = code_str.lower().strip()
        matching = [c for c in target_list if c["code"].lower() == code_clean]
        if not matching:
            msg = f"Coo coo! ⚠️ Card `{code_str}` is not in your offered trade list!"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await interaction_or_ctx.response.send_message(msg, ephemeral=True)
            else:
                await interaction_or_ctx.send(msg)
            return

        target_list.remove(matching[0])

        self.p1_confirmed = False
        self.p2_confirmed = False

        if isinstance(interaction_or_ctx, discord.Interaction):
            await self.update_message(interaction_or_ctx)
        else:
            await self.update_message()

    async def confirm_user(self, interaction_or_ctx, user_id: int):
        if user_id == self.p1.id:
            self.p1_confirmed = True
        elif user_id == self.p2.id:
            self.p2_confirmed = True

        if self.p1_confirmed and self.p2_confirmed:
            p1_codes = [c["code"] for c in self.p1_cards]
            p2_codes = [c["code"] for c in self.p2_cards]

            success = transfer_cards_between_users(self.p1.id, p1_codes, self.p2.id, p2_codes)
            if success:
                p1_rec_text = ""
                if self.p2_cards:
                    for c in self.p2_cards:
                        p1_rec_text += f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})\n"
                else:
                    p1_rec_text = "*None (Gift)*\n"

                p2_rec_text = ""
                if self.p1_cards:
                    for c in self.p1_cards:
                        p2_rec_text += f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})\n"
                else:
                    p2_rec_text = "*None (Gift)*\n"

                embed = discord.Embed(
                    title="🎉 Trade Completed Successfully!",
                    description=f"🤝 **{self.p1.mention}** and **{self.p2.mention}** have completed their trade!",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name=f"📦 {self.p1.display_name} received:",
                    value=p1_rec_text,
                    inline=False
                )
                embed.add_field(
                    name=f"📦 {self.p2.display_name} received:",
                    value=p2_rec_text,
                    inline=False
                )

                for child in self.view.children:
                    child.disabled = True
                if isinstance(interaction_or_ctx, discord.Interaction):
                    await interaction_or_ctx.response.edit_message(embed=embed, view=self.view)
                else:
                    await self.message.edit(embed=embed, view=self.view)
            else:
                msg = "Coo coo! ⚠️ Database transfer error occurred during trade!"
                if isinstance(interaction_or_ctx, discord.Interaction):
                    await interaction_or_ctx.response.send_message(msg, ephemeral=True)
                else:
                    await interaction_or_ctx.send(msg)

            if self.channel.id in ACTIVE_TRADES:
                del ACTIVE_TRADES[self.channel.id]
        else:
            if isinstance(interaction_or_ctx, discord.Interaction):
                await self.update_message(interaction_or_ctx)
            else:
                await self.update_message()

    async def cancel_trade(self, interaction_or_ctx, user: discord.User):
        embed = discord.Embed(
            title="❌ Trade Cancelled",
            description=f"Trade session was cancelled by {user.mention}.",
            color=discord.Color.red()
        )
        for child in self.view.children:
            child.disabled = True

        if isinstance(interaction_or_ctx, discord.Interaction):
            await interaction_or_ctx.response.edit_message(embed=embed, view=self.view)
        else:
            await self.message.edit(embed=embed, view=self.view)

        if self.channel.id in ACTIVE_TRADES:
            del ACTIVE_TRADES[self.channel.id]

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
            f"⏳ **Priority:** {user.mention} has 10 seconds of exclusive drop priority!\n"
            f"Click a button below to grab a card!"
        ),
        color=discord.Color.gold()
    )
    embed.set_image(url="attachment://drop.png")
    embed.set_footer(text="Coo Coo Card Engine • Side-By-Side View")

    view = CardDropView(cards, dropper_id=user.id)

    if isinstance(ctx_or_interaction, discord.Interaction):
        msg = await ctx_or_interaction.followup.send(embed=embed, file=file, view=view)
        view.message = msg
    else:
        msg = await ctx_or_interaction.send(embed=embed, file=file, view=view)
        view.message = msg

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

@bot.command(name="d")
async def drop_prefix_d(ctx):
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
        embed.set_footer(text=f"Showing 10 of {len(rows)} cards. Type /card code:<code> to see full card artwork!")
    else:
        embed.set_footer(text="Type /card code:<code> to see full card artwork!")

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

@bot.command(name="i")
async def inventory_prefix_i(ctx):
    await inventory_prefix(ctx)

@bot.command(name="inv")
async def inventory_prefix_inv(ctx):
    await inventory_prefix(ctx)

async def process_view_card(ctx_or_interaction, card_code_query: str = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not card_code_query:
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

@bot.tree.command(name="card", description="View full details and artwork of a card (Defaults to your latest card)")
async def card_slash(interaction: discord.Interaction, code: str = None):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_view_card(interaction, code)

@bot.tree.command(name="view", description="View full details and artwork of a card (Defaults to your latest card)")
async def view_slash(interaction: discord.Interaction, code: str = None):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_view_card(interaction, code)

@bot.command(name="v")
async def view_card_prefix_v(ctx, code: str = None):
    await process_view_card(ctx, code)

@bot.command(name="view")
async def view_card_prefix_view(ctx, code: str = None):
    await process_view_card(ctx, code)

@bot.command(name="card")
async def view_card_prefix_card(ctx, code: str = None):
    await process_view_card(ctx, code)

# ==========================================
# 🔄 TRADING COMMANDS & SHORTCUTS
# ==========================================
async def start_trade_session(ctx_or_interaction, partner: discord.User):
    author = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    channel = ctx_or_interaction.channel

    if partner.bot:
        msg = "Coo coo! ⚠️ You cannot trade with bots!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    if partner.id == author.id:
        msg = "Coo coo! ⚠️ You cannot trade with yourself!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    if channel.id in ACTIVE_TRADES:
        msg = "Coo coo! ⚠️ There is already an active trade session in this channel!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    session = TradeSession(channel, author, partner)
    ACTIVE_TRADES[channel.id] = session

    embed = session.render_embed()

    if isinstance(ctx_or_interaction, discord.Interaction):
        msg = await ctx_or_interaction.followup.send(embed=embed, view=session.view)
        session.message = msg
    else:
        msg = await ctx_or_interaction.send(embed=embed, view=session.view)
        session.message = msg

@bot.tree.command(name="trade", description="Initiates a Karuta-style card trade with another player")
async def trade_slash(interaction: discord.Interaction, partner: discord.User):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await start_trade_session(interaction, partner)

@bot.command(name="trade")
async def trade_prefix(ctx, partner: discord.User):
    await start_trade_session(ctx, partner)

@bot.command(name="t")
async def trade_prefix_shortcut(ctx, partner: discord.User):
    await start_trade_session(ctx, partner)

@bot.command(name="ta")
async def trade_add_prefix(ctx, code: str):
    if ctx.channel.id not in ACTIVE_TRADES:
        await ctx.send("Coo coo! ⚠️ There is no active trade session in this channel!")
        return
    session = ACTIVE_TRADES[ctx.channel.id]
    if ctx.author.id not in [session.p1.id, session.p2.id]:
        await ctx.send("Coo coo! ⚠️ You are not part of the active trade in this channel!")
        return
    await session.add_card(ctx, code)

@bot.command(name="tr")
async def trade_remove_prefix(ctx, code: str):
    if ctx.channel.id not in ACTIVE_TRADES:
        await ctx.send("Coo coo! ⚠️ There is no active trade session in this channel!")
        return
    session = ACTIVE_TRADES[ctx.channel.id]
    if ctx.author.id not in [session.p1.id, session.p2.id]:
        await ctx.send("Coo coo! ⚠️ You are not part of the active trade in this channel!")
        return
    await session.remove_card(ctx, code)

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
