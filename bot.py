import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import random
import asyncio
import aiohttp
from aiohttp import web
import sqlite3
import time
import string
import io
import traceback
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATA_DIR = os.getenv("DATA_DIR", "/data")
if os.path.exists(DATA_DIR):
    DB_PATH = os.path.join(DATA_DIR, "inventory.db")
    repo_db = os.path.join(os.path.dirname(__file__), "inventory.db")
    
    needs_seed = False
    if not os.path.exists(DB_PATH):
        needs_seed = True
    else:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5.0)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM cards_pool")
            cnt = cur.fetchone()[0]
            conn.close()
            if cnt == 0:
                needs_seed = True
        except Exception:
            needs_seed = True

    if needs_seed and os.path.exists(repo_db):
        try:
            import shutil
            shutil.copyfile(repo_db, DB_PATH)
            print("📦 Successfully seeded Railway /data volume with 10,004 character master database!")
        except Exception as e:
            print(f"Volume seed warning: {e}")
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

# ==========================================
# 🤖 BOT DISCORD CLIENT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None, case_insensitive=True)

def generate_card_code() -> str:
    """Generates a random 6-character alphanumeric card code (e.g. 136hma)."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=6))

# ==========================================
# 🗄️ SQLITE DATABASE INITIALIZATION & ECONOMY
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
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
        tag TEXT DEFAULT NULL,
        grabbed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("PRAGMA table_info(inventory)")
    inv_columns = [column[1] for column in cursor.fetchall()]
    if "code" not in inv_columns:
        cursor.execute("ALTER TABLE inventory ADD COLUMN code TEXT")
    if "edition" not in inv_columns:
        cursor.execute("ALTER TABLE inventory ADD COLUMN edition INTEGER DEFAULT 1")
    if "tag" not in inv_columns:
        cursor.execute("ALTER TABLE inventory ADD COLUMN tag TEXT DEFAULT NULL")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mints (
        character_name TEXT PRIMARY KEY,
        current_mint INTEGER NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        gems INTEGER DEFAULT 100,
        dust INTEGER DEFAULT 0,
        last_daily INTEGER DEFAULT 0,
        last_drop INTEGER DEFAULT 0,
        last_grab INTEGER DEFAULT 0
    )
    """)

    cursor.execute("PRAGMA table_info(users)")
    usr_columns = [column[1] for column in cursor.fetchall()]
    if "dust" not in usr_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN dust INTEGER DEFAULT 0")
    if "last_drop" not in usr_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_drop INTEGER DEFAULT 0")
    if "last_grab" not in usr_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_grab INTEGER DEFAULT 0")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cards_pool (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anilist_id INTEGER UNIQUE,
        character_name TEXT NOT NULL,
        series_name TEXT NOT NULL,
        image_url TEXT NOT NULL,
        favourites INTEGER DEFAULT 0,
        rarity TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

init_db()

def get_user_gems(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT gems FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, 100, 0)", (user_id,))
        conn.commit()
        gems = 100
    else:
        gems = row[0]
    conn.close()
    return gems

def get_user_dust(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT dust FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, 100, 0)", (user_id,))
        conn.commit()
        dust = 0
    else:
        dust = row[0] if row[0] is not None else 0
    conn.close()
    return dust

def add_user_gems(user_id: int, amount: int) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT gems FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        new_gems = 100 + amount
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, ?, 0)", (user_id, new_gems))
    else:
        new_gems = row[0] + amount
        cursor.execute("UPDATE users SET gems = ? WHERE user_id = ?", (new_gems, user_id))
    conn.commit()
    conn.close()
    return new_gems

def add_user_dust(user_id: int, amount: int) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT dust FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        new_dust = amount
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, 100, ?)", (user_id, new_dust))
    else:
        curr = row[0] if row[0] is not None else 0
        new_dust = curr + amount
        cursor.execute("UPDATE users SET dust = ? WHERE user_id = ?", (new_dust, user_id))
    conn.commit()
    conn.close()
    return new_dust

def transfer_gems(from_user_id: int, to_user_id: int, amount: int) -> bool:
    if amount <= 0:
        return False
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT gems FROM users WHERE user_id = ?", (from_user_id,))
        row1 = cursor.fetchone()
        from_gems = row1[0] if row1 else 0

        if from_gems < amount:
            conn.close()
            return False

        # Deduct
        cursor.execute("UPDATE users SET gems = gems - ? WHERE user_id = ?", (amount, from_user_id))

        # Credit
        cursor.execute("SELECT gems FROM users WHERE user_id = ?", (to_user_id,))
        row2 = cursor.fetchone()
        if not row2:
            cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, ?, 0)", (to_user_id, 100 + amount))
        else:
            cursor.execute("UPDATE users SET gems = gems + ? WHERE user_id = ?", (amount, to_user_id))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error transferring gems: {e}")
        conn.rollback()
        conn.close()
        return False

def get_next_mint(character_name: str) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
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
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO inventory (user_id, code, character_name, series_name, image_url, rarity, mint_number, edition)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, code, character_name, series_name, image_url, rarity, mint_number, edition))
    inserted_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inserted_id

def get_user_inventory(user_id: int, tag_filter: str = None):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    if tag_filter:
        cursor.execute("SELECT id, code, character_name, series_name, rarity, mint_number, edition, image_url, tag FROM inventory WHERE user_id = ? AND LOWER(tag) = ? ORDER BY id DESC", (user_id, tag_filter.lower().strip()))
    else:
        cursor.execute("SELECT id, code, character_name, series_name, rarity, mint_number, edition, image_url, tag FROM inventory WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_card_by_code_and_owner(code: str, user_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, tag FROM inventory WHERE (code = ? OR id = ?) AND user_id = ?", (code.lower().strip(), code.strip(), user_id))
    row = cursor.fetchone()
    conn.close()
    return row

def update_card_tag(code_str: str, user_id: int, tag_name: str = None) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    query_str = code_str.lower().strip()
    cursor.execute("UPDATE inventory SET tag = ? WHERE (code = ? OR id = ?) AND user_id = ?", (tag_name, query_str, query_str, user_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def delete_card_from_inventory(code_str: str, user_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    query_str = code_str.lower().strip()
    cursor.execute("SELECT id, code, character_name, rarity FROM inventory WHERE (code = ? OR id = ?) AND user_id = ?", (query_str, query_str, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    cursor.execute("DELETE FROM inventory WHERE id = ?", (row[0],))
    conn.commit()
    conn.close()
    return row

def transfer_cards_between_users(user1_id: int, user1_codes: list, user2_id: int, user2_codes: list):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
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

def get_user_cooldowns(user_id: int):
    """Returns timestamps for last_drop, last_grab, last_daily."""
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT last_drop, last_grab, last_daily FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return 0, 0, 0
    return (row[0] or 0), (row[1] or 0), (row[2] or 0)

def set_user_cooldown(user_id: int, cd_type: str, ts: int):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, 100, 0)", (user_id,))
    
    if cd_type == "drop":
        cursor.execute("UPDATE users SET last_drop = ? WHERE user_id = ?", (ts, user_id))
    elif cd_type == "grab":
        cursor.execute("UPDATE users SET last_grab = ? WHERE user_id = ?", (ts, user_id))
    elif cd_type == "daily":
        cursor.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (ts, user_id))
    conn.commit()
    conn.close()

# ==========================================
# 🎲 WEIGHTED RARITY DROP PROBABILITIES
# ==========================================
RARITY_WEIGHTS = [
    ("⚪ Common", 0.76),     # 76% Drop Rate
    ("🔷 Rare", 0.15),       # 15% Drop Rate
    ("🟣 Epic", 0.08),       #  8% Drop Rate
    ("✨ Legendary", 0.01)   #  1% Drop Rate
]

def sample_rarity() -> str:
    rarities, weights = zip(*RARITY_WEIGHTS)
    return random.choices(rarities, weights=weights, k=1)[0]

def get_cards_from_db_pool(count: int = 3):
    """Fetches cards using weighted rarity probabilities (76% Common, 15% Rare, 8% Epic, 1% Legendary)."""
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()

    cards = []
    for _ in range(count):
        target_rarity = sample_rarity()
        cursor.execute("""
        SELECT character_name, series_name, image_url, rarity
        FROM cards_pool
        WHERE rarity = ?
        ORDER BY RANDOM()
        LIMIT 1
        """, (target_rarity,))
        row = cursor.fetchone()
        
        # Fallback if pool doesn't have a card matching target rarity
        if not row:
            cursor.execute("SELECT character_name, series_name, image_url, rarity FROM cards_pool ORDER BY RANDOM() LIMIT 1")
            row = cursor.fetchone()

        if row:
            char_name, series, img_url, rarity = row
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

    conn.close()
    return cards

# ==========================================
# 🎨 PIL KARUTA REFERENCE-MATCHING RENDERER
# ==========================================
RARITY_COLORS = {
    "✨ Legendary": (255, 215, 0),   # Gold
    "🟣 Epic": (147, 112, 219),     # Rich Purple
    "🔷 Rare": (0, 229, 255),       # Cyan Blue
    "⚪ Common": (140, 155, 170)    # Slate Silver
}

BURN_REWARDS = {
    "✨ Legendary": {"dust": 200},
    "🟣 Epic": {"dust": 100},
    "🔷 Rare": {"dust": 50},
    "⚪ Common": {"dust": 20}
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
        
        draw.rectangle([x, y, x + card_w, y + card_h], fill=(28, 30, 34, 255), outline=(60, 65, 75), width=2)
        draw.rectangle([x + 4, y + 4, x + card_w - 4, y + card_h - 4], outline=rc, width=2)
        
        raw_img = raw_images[idx]
        img_w, img_h = card_w - 14, card_h - 68
        resized_img = raw_img.resize((img_w, img_h), Image.Resampling.LANCZOS)
        canvas.paste(resized_img, (x + 7, y + 7))
        
        badge_poly = [(x + 4, y + 4), (x + 38, y + 4), (x + 44, y + 16), (x + 38, y + 34), (x + 4, y + 34)]
        draw.polygon(badge_poly, fill=(15, 16, 18), outline=rc)
        draw.text((x + 16, y + 10), str(idx + 1), fill=(255, 255, 255))
        
        box_y1 = y + card_h - 60
        box_y2 = y + card_h - 6
        draw.rectangle([x + 6, box_y1, x + card_w - 6, box_y2], fill=(12, 13, 15, 245))
        draw.line([x + 10, box_y1 + 8, x + 10, box_y2 - 8], fill=rc, width=3)
        
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
# 🌐 ANILIST PUBLIC API INTEGRATION (FALLBACK)
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
# 🎴 CARD DROP BUTTON UI & COOLDOWNS
# ==========================================
DROP_COOLDOWN_SEC = 900  # 15 Minutes
GRAB_COOLDOWN_SEC = 300  # 5 Minutes
DAILY_COOLDOWN_SEC = 86400  # 24 Hours

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

        now_ts = int(time.time())

        # Check Grab Cooldown (5 Minutes)
        l_drop, l_grab, l_daily = get_user_cooldowns(interaction.user.id)
        elapsed_grab = now_ts - l_grab
        if elapsed_grab < GRAB_COOLDOWN_SEC:
            rem = GRAB_COOLDOWN_SEC - elapsed_grab
            mins = rem // 60
            secs = rem % 60
            await interaction.response.send_message(
                f"Coo coo! ⏳ Your **Grab** is on cooldown! Return in **{mins}m {secs}s**! Type `!cd` to view all your cooldowns.",
                ephemeral=True
            )
            return

        # Check 5 Minutes Exclusive Priority Window for the Dropper
        elapsed_drop = time.time() - view.drop_time
        if elapsed_drop < 300.0 and interaction.user.id != view.dropper_id:
            rem_prio = int(300.0 - elapsed_drop) + 1
            p_mins = rem_prio // 60
            p_secs = rem_prio % 60
            await interaction.response.send_message(
                f"Coo coo! ⏳ <@{view.dropper_id}> has **5 minutes of drop priority**! ({p_mins}m {p_secs}s remaining)",
                ephemeral=True
            )
            return

        view.claimed = True
        set_user_cooldown(interaction.user.id, "grab", now_ts)
        
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
        super().__init__(timeout=300)  # 5 Minute drop view active timeout
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
# ⏱️ COOLDOWNS COMMAND
# ==========================================
async def process_cooldowns(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    now_ts = int(time.time())
    l_drop, l_grab, l_daily = get_user_cooldowns(user.id)

    # Calculate Drop CD (15 min)
    drop_elapsed = now_ts - l_drop
    if drop_elapsed >= DROP_COOLDOWN_SEC:
        drop_status = "✅ **Ready to Drop!** (`/drop` or `!d`)"
    else:
        rem_d = DROP_COOLDOWN_SEC - drop_elapsed
        d_m = rem_d // 60
        d_s = rem_d % 60
        drop_status = f"⏳ Ready in **{d_m}m {d_s}s**"

    # Calculate Grab CD (5 min)
    grab_elapsed = now_ts - l_grab
    if grab_elapsed >= GRAB_COOLDOWN_SEC:
        grab_status = "✅ **Ready to Grab!**"
    else:
        rem_g = GRAB_COOLDOWN_SEC - grab_elapsed
        g_m = rem_g // 60
        g_s = rem_g % 60
        grab_status = f"⏳ Ready in **{g_m}m {g_s}s**"

    # Calculate Daily CD (24 hrs)
    daily_elapsed = now_ts - l_daily
    if daily_elapsed >= DAILY_COOLDOWN_SEC:
        daily_status = "✅ **Ready to Claim!** (`/daily` or `!daily`)"
    else:
        rem_day = DAILY_COOLDOWN_SEC - daily_elapsed
        day_h = rem_day // 3600
        day_m = (rem_day % 3600) // 60
        day_s = rem_day % 60
        daily_status = f"⏳ Ready in **{day_h}h {day_m}m {day_s}s**"

    embed = discord.Embed(
        title=f"⏱️ {user.display_name}'s Command Cooldowns",
        description=f"Below are your current command timers:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🎴 Card Drop Cooldown (15m)",
        value=drop_status,
        inline=False
    )
    embed.add_field(
        name="🖐️ Card Grab Cooldown (5m)",
        value=grab_status,
        inline=False
    )
    embed.add_field(
        name="🎁 Daily Gems Cooldown (24h)",
        value=daily_status,
        inline=False
    )

    embed.set_footer(text="Coo Coo Timers • Type /drop to collect new cards!")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="cd", description="Check your current Drop, Grab, and Daily command cooldowns")
async def cd_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_cooldowns(interaction)

@bot.tree.command(name="cooldowns", description="Check your current Drop, Grab, and Daily command cooldowns")
async def cooldowns_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_cooldowns(interaction)

@bot.command(name="cd")
async def cd_prefix(ctx):
    await process_cooldowns(ctx)

@bot.command(name="cooldowns")
async def cooldowns_prefix(ctx):
    await process_cooldowns(ctx)

# ==========================================
# 🔄 KARUTA-STYLE TRADING ENGINE WITH GEMS
# ==========================================
ACTIVE_TRADES = {}  # {channel_id: TradeSession}

class AddCardModal(discord.ui.Modal, title="Offer Card or Gems"):
    input_val = discord.ui.TextInput(
        label="Card ID or Gems Amount",
        placeholder="Enter 6-char Card ID (e.g. 136hma) OR Gems (e.g. 250g or 250gems)",
        min_length=1,
        max_length=15,
        required=True
    )

    def __init__(self, trade_session):
        super().__init__()
        self.trade_session = trade_session

    async def on_submit(self, interaction: discord.Interaction):
        val = self.input_val.value.strip().lower()
        if val.endswith("g") or val.endswith("gems") or val.isdigit():
            clean_num = val.rstrip("gems").rstrip("g").strip()
            if clean_num.isdigit():
                await self.trade_session.set_gems(interaction, int(clean_num))
                return
        await self.trade_session.add_card(interaction, self.input_val.value.strip())

class RemoveCardModal(discord.ui.Modal, title="Remove Card or Reset Gems"):
    input_val = discord.ui.TextInput(
        label="Card ID to Remove (or 'gems' to reset gems)",
        placeholder="Enter Card ID currently in trade or type 'gems'",
        min_length=1,
        max_length=15,
        required=True
    )

    def __init__(self, trade_session):
        super().__init__()
        self.trade_session = trade_session

    async def on_submit(self, interaction: discord.Interaction):
        val = self.input_val.value.strip().lower()
        if val in ["gems", "gem", "g"]:
            await self.trade_session.set_gems(interaction, 0)
            return
        await self.trade_session.remove_card(interaction, self.input_val.value.strip())

class TradeView(discord.ui.View):
    def __init__(self, trade_session):
        super().__init__(timeout=300)
        self.trade_session = trade_session

    @discord.ui.button(label="Offer Card / Gems", style=discord.ButtonStyle.primary, emoji="➕")
    async def offer_card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.trade_session.p1.id, self.trade_session.p2.id]:
            await interaction.response.send_message("Coo coo! ⚠️ You are not part of this trade session!", ephemeral=True)
            return
        await interaction.response.send_modal(AddCardModal(self.trade_session))

    @discord.ui.button(label="Remove Offer", style=discord.ButtonStyle.secondary, emoji="➖")
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
        self.p1_gems = 0
        self.p2_gems = 0
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

        p1_items = []
        if self.p1_gems > 0:
            p1_items.append(f"• 💎 **{self.p1_gems:,} Gems**")
        if self.p1_cards:
            for c in self.p1_cards:
                p1_items.append(f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})")

        p1_text = "\n".join(p1_items) if p1_items else "*No items offered yet*"
        p1_status = "✅ **CONFIRMED**" if self.p1_confirmed else "⏳ *Waiting...*"

        p2_items = []
        if self.p2_gems > 0:
            p2_items.append(f"• 💎 **{self.p2_gems:,} Gems**")
        if self.p2_cards:
            for c in self.p2_cards:
                p2_items.append(f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})")

        p2_text = "\n".join(p2_items) if p2_items else "*No items offered yet*"
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
        embed.set_footer(text="Offer cards/gems via buttons or type !ta <code_or_amountG> in chat!")
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

    async def set_gems(self, interaction_or_ctx, amount: int):
        is_p1 = (interaction_or_ctx.user.id if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.author.id) == self.p1.id
        user = self.p1 if is_p1 else self.p2

        if amount < 0:
            msg = "Coo coo! ⚠️ Gem offer cannot be negative!"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await interaction_or_ctx.response.send_message(msg, ephemeral=True)
            else:
                await interaction_or_ctx.send(msg)
            return

        user_balance = get_user_gems(user.id)
        if amount > user_balance:
            msg = f"Coo coo! ⚠️ You only have **{user_balance:,} 💎 Gems** in your balance!"
            if isinstance(interaction_or_ctx, discord.Interaction):
                await interaction_or_ctx.response.send_message(msg, ephemeral=True)
            else:
                await interaction_or_ctx.send(msg)
            return

        if is_p1:
            self.p1_gems = amount
        else:
            self.p2_gems = amount

        self.p1_confirmed = False
        self.p2_confirmed = False

        if isinstance(interaction_or_ctx, discord.Interaction):
            await self.update_message(interaction_or_ctx)
        else:
            await self.update_message()

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

        cid, code, uid, char_name, series, rarity, mint_num, edition, tag = card_row
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

            card_success = transfer_cards_between_users(self.p1.id, p1_codes, self.p2.id, p2_codes)

            gem_success_1 = True
            if self.p1_gems > 0:
                gem_success_1 = transfer_gems(self.p1.id, self.p2.id, self.p1_gems)

            gem_success_2 = True
            if self.p2_gems > 0:
                gem_success_2 = transfer_gems(self.p2.id, self.p1.id, self.p2_gems)

            if card_success and gem_success_1 and gem_success_2:
                p1_rec_items = []
                if self.p2_gems > 0:
                    p1_rec_items.append(f"• 💎 **{self.p2_gems:,} Gems**")
                if self.p2_cards:
                    for c in self.p2_cards:
                        p1_rec_items.append(f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})")
                p1_rec_text = "\n".join(p1_rec_items) if p1_rec_items else "*None (Gift)*\n"

                p2_rec_items = []
                if self.p1_gems > 0:
                    p2_rec_items.append(f"• 💎 **{self.p1_gems:,} Gems**")
                if self.p1_cards:
                    for c in self.p1_cards:
                        p2_rec_text.append(f"• `{c['code']}` — **{c['character_name']}** ({c['rarity']})")
                p2_rec_text = "\n".join(p2_rec_items) if p2_rec_items else "*None (Gift)*\n"

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
# 🤖 BOT DISCORD CLIENT SETUP & HEALTHCHECK
# ==========================================
async def handle_healthcheck(request):
    return web.Response(text="Coo Coo Bot is Healthy and Online 24/7! 🐦🎴")

async def start_healthcheck_server():
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    app.router.add_get("/health", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Railway HTTP Healthcheck Server active on port {port}!")

@bot.event
async def on_ready():
    print(f"🐦 Coo Coo is ONLINE as {bot.user.name} ({bot.user.id})!")
    bot.loop.create_task(start_healthcheck_server())
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
                f"Here, take a fresh pretzel crust 🥨 and **100 starter Gems 💎**!"
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
# 💎 GEMS ECONOMY COMMANDS
# ==========================================
async def process_balance(ctx_or_interaction):
    target = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    gems = get_user_gems(target.id)

    embed = discord.Embed(
        title=f"💎 {target.display_name}'s Gem Pouch",
        description=f"Current Balance: **{gems:,} Gems 💎**",
        color=discord.Color.from_rgb(0, 229, 255)
    )
    embed.set_footer(text="Type !daily or /daily to claim 500 free Gems every 24 hours!")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.followup.send(embed=embed, ephemeral=True)
    else:
        try:
            await ctx_or_interaction.author.send(embed=embed)
            await ctx_or_interaction.message.reply("Coo coo! 📩 Sent your Gem balance to your DMs so it stays private!", delete_after=5)
        except Exception:
            await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="bal", description="Check your private personal Gems balance")
async def bal_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        pass
    await process_balance(interaction)

@bot.tree.command(name="balance", description="Check your private personal Gems balance")
async def balance_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except Exception:
        pass
    await process_balance(interaction)

@bot.command(name="balance")
async def balance_prefix(ctx):
    await process_balance(ctx)

@bot.command(name="bal")
async def balance_prefix_bal(ctx):
    await process_balance(ctx)

@bot.command(name="gems")
async def balance_prefix_gems(ctx):
    await process_balance(ctx)

async def process_daily(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    now_ts = int(time.time())

    l_drop, l_grab, last_daily = get_user_cooldowns(user.id)
    elapsed = now_ts - last_daily

    if elapsed < DAILY_COOLDOWN_SEC:
        remaining = DAILY_COOLDOWN_SEC - elapsed
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        seconds = remaining % 60

        msg = f"Coo coo! ⏳ You have already claimed your daily Gems! Return in **{hours}h {minutes}m {seconds}s**! Type `!cd` to view your cooldowns."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    reward = 500
    current_gems = get_user_gems(user.id)
    new_gems = current_gems + reward
    
    add_user_gems(user.id, reward)
    set_user_cooldown(user.id, "daily", now_ts)

    embed = discord.Embed(
        title="🎁 Daily Reward Claimed!",
        description=(
            f"Coo coo! 🐦 You claimed **+500 💎 Gems**!\n\n"
            f"💎 **New Balance:** **{new_gems:,} Gems**\n"
            f"⏰ Next Daily available in **24 hours**!"
        ),
        color=discord.Color.green()
    )

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="daily", description="Claim your daily 500 Gems reward (Available every 24 hours)")
async def daily_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_daily(interaction)

@bot.command(name="daily")
async def daily_prefix(ctx):
    await process_daily(ctx)

async def process_pay(ctx_or_interaction, target: discord.User, amount: int):
    sender = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author

    if target.bot:
        msg = "Coo coo! ⚠️ You cannot send Gems to bots!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    if target.id == sender.id:
        msg = "Coo coo! ⚠️ You cannot pay Gems to yourself!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    if amount <= 0:
        msg = "Coo coo! ⚠️ Amount must be greater than 0 Gems!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    success = transfer_gems(sender.id, target.id, amount)
    if success:
        embed = discord.Embed(
            title="💸 Gems Transferred!",
            description=f"Successfully sent **{amount:,} 💎 Gems** to {target.mention}!",
            color=discord.Color.gold()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    else:
        sender_gems = get_user_gems(sender.id)
        msg = f"Coo coo! ⚠️ You don't have enough Gems! You only have **{sender_gems:,} 💎**!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)

@bot.tree.command(name="pay", description="Transfer Gems directly to another player")
async def pay_slash(interaction: discord.Interaction, target: discord.User, amount: int):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_pay(interaction, target, amount)

@bot.command(name="pay")
async def pay_prefix(ctx, target: discord.User, amount: int):
    await process_pay(ctx, target, amount)

@bot.command(name="give")
async def pay_prefix_give(ctx, target: discord.User, amount: int):
    await process_pay(ctx, target, amount)

# ==========================================
# 🧪 BURN, DUST & TAGGING SYSTEM
# ==========================================
class BurnConfirmView(discord.ui.View):
    def __init__(self, owner_id: int, card_code: str, char_name: str, rarity: str, dust_reward: int):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.card_code = card_code
        self.char_name = char_name
        self.rarity = rarity
        self.dust_reward = dust_reward

    @discord.ui.button(label="Confirm Burn", style=discord.ButtonStyle.danger, emoji="🔥")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot confirm this burn!", ephemeral=True)
            return

        deleted = delete_card_from_inventory(self.card_code, self.owner_id)
        if not deleted:
            await interaction.response.send_message(f"Coo coo! ⚠️ Card `{self.card_code}` is no longer in your inventory!", ephemeral=True)
            return

        new_dust = add_user_dust(self.owner_id, self.dust_reward)
        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title=f"🔥 Burned: {self.char_name}",
            description=(
                f"🔥 **{interaction.user.mention}** confirmed and burned `{self.card_code}` (**{self.char_name}** — {self.rarity}) into ashes!\n\n"
                f"🧪 **Gained Dust:** **+{self.dust_reward} Dust** *(Total Balance: {new_dust:,} 🧪 Dust)*"
            ),
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Coo coo! ⚠️ You cannot cancel this burn!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="❌ Burn Cancelled",
            description=f"Safe! **{self.char_name}** (`{self.card_code}`) was saved from the flames.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self)

async def process_dust_balance(ctx_or_interaction):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    dust = get_user_dust(user.id)

    embed = discord.Embed(
        title=f"🧪 {user.display_name}'s Dust Flask",
        description=f"Current Balance: **{dust:,} Dust 🧪**",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Burn duplicate or unwanted cards with !burn <card_id> to generate Dust!")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="dust", description="Check your current Dust flask balance")
async def dust_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_dust_balance(interaction)

@bot.command(name="dust")
async def dust_prefix(ctx):
    await process_dust_balance(ctx)

async def process_burn_card(ctx_or_interaction, card_code: str):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    card_row = get_card_by_code_and_owner(card_code, user.id)

    if not card_row:
        msg = f"Coo coo! ⚠️ Card `{card_code}` not found in your inventory!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    cid, code, uid, char_name, series, rarity, mint_num, edition, tag = card_row
    code_str = code if code else f"c{cid:04d}"
    rewards = BURN_REWARDS.get(rarity, {"dust": 20})

    if rarity in ["🟣 Epic", "✨ Legendary"]:
        view = BurnConfirmView(user.id, code_str, char_name, rarity, rewards["dust"])
        embed = discord.Embed(
            title=f"⚠️ Are you sure you want to burn this {rarity} card?",
            description=(
                f"🔥 You are about to burn **{char_name}** (`{code_str}`) — **{rarity}**!\n"
                f"🧪 **Yield:** **+{rewards['dust']} Dust**\n\n"
                f"⚠️ *This action is permanent and cannot be undone! Click below to confirm.*"
            ),
            color=discord.Color.dark_orange()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed, view=view)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)
        return

    deleted = delete_card_from_inventory(code_str, user.id)
    if not deleted:
        msg = f"Coo coo! ⚠️ Error burning card `{code_str}`!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    new_dust = add_user_dust(user.id, rewards["dust"])
    embed = discord.Embed(
        title=f"🔥 Burned: {char_name}",
        description=(
            f"🔥 **{user.mention}** burned `{code_str}` (**{char_name}** — {rarity}) into ashes!\n\n"
            f"🧪 **Gained Dust:** **+{rewards['dust']} Dust** *(Total Balance: {new_dust:,} 🧪 Dust)*"
        ),
        color=discord.Color.red()
    )

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="burn", description="Burn an unwanted card to convert it into Dust")
async def burn_slash(interaction: discord.Interaction, code: str):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_burn_card(interaction, code)

@bot.command(name="burn")
async def burn_prefix(ctx, code: str):
    await process_burn_card(ctx, code)

async def process_tag_card(ctx_or_interaction, code: str, tag_name: str):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    clean_tag = tag_name.strip()

    success = update_card_tag(code, user.id, clean_tag)
    if success:
        embed = discord.Embed(
            title="🏷️ Card Tagged!",
            description=f"Successfully assigned tag **`[{clean_tag}]`** to card `{code.lower()}`!",
            color=discord.Color.blue()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    else:
        msg = f"Coo coo! ⚠️ Card `{code}` not found in your inventory!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)

@bot.tree.command(name="tag", description="Assign a custom folder tag to a card")
async def tag_slash(interaction: discord.Interaction, code: str, tag: str):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_tag_card(interaction, code, tag)

@bot.command(name="tag")
async def tag_prefix(ctx, code: str, *, tag: str):
    await process_tag_card(ctx, code, tag)

async def process_untag_card(ctx_or_interaction, code: str):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    success = update_card_tag(code, user.id, None)

    if success:
        embed = discord.Embed(
            title="🏷️ Card Untagged!",
            description=f"Removed tag from card `{code.lower()}`!",
            color=discord.Color.dark_grey()
        )
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)
    else:
        msg = f"Coo coo! ⚠️ Card `{code}` not found in your inventory!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)

@bot.tree.command(name="untag", description="Remove a folder tag from a card")
async def untag_slash(interaction: discord.Interaction, code: str):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_untag_card(interaction, code)

@bot.command(name="untag")
async def untag_prefix(ctx, code: str):
    await process_untag_card(ctx, code)

@bot.tree.command(name="vt", description="View all cards in a specific tag folder")
async def vt_slash(interaction: discord.Interaction, tag: str):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_inventory(interaction, tag)

@bot.tree.command(name="viewtag", description="View all cards in a specific tag folder")
async def viewtag_slash(interaction: discord.Interaction, tag: str):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_inventory(interaction, tag)

@bot.command(name="vt")
async def view_tag_prefix_vt(ctx, *, tag: str):
    await process_inventory(ctx, tag)

@bot.command(name="viewtag")
async def view_tag_prefix_viewtag(ctx, *, tag: str):
    await process_inventory(ctx, tag)

# ==========================================
# 🎴 ANILIST CARD DROP & INVENTORY COMMANDS
# ==========================================

async def execute_card_drop(ctx_or_interaction, user):
    """Core logic to fetch cards from local DB pool and render a single horizontal 3-card side-by-side image!"""
    now_ts = int(time.time())
    l_drop, l_grab, l_daily = get_user_cooldowns(user.id)
    elapsed_drop = now_ts - l_drop

    if elapsed_drop < DROP_COOLDOWN_SEC:
        rem = DROP_COOLDOWN_SEC - elapsed_drop
        mins = rem // 60
        secs = rem % 60
        msg = f"Coo coo! ⏳ Your **Drop** is on cooldown! Return in **{mins}m {secs}s**! Type `!cd` to check your cooldowns."
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    cards = get_cards_from_db_pool(3)
    if not cards or len(cards) < 3:
        cards = await fetch_random_anilist_cards(3)

    if not cards:
        msg = "Coo coo! ⚠️ Couldn't fetch cards for drop. Please try again in a moment!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    set_user_cooldown(user.id, "drop", now_ts)

    buf = await render_three_cards_composite(cards)
    file = discord.File(fp=buf, filename="drop.png")

    embed = discord.Embed(
        title=f"🎴 {user.display_name}'s Card Drop!",
        description=(
            f"1️⃣ **{cards[0]['name']}** · *{cards[0]['series']}*\n"
            f"2️⃣ **{cards[1]['name']}** · *{cards[1]['series']}*\n"
            f"3️⃣ **{cards[2]['name']}** · *{cards[2]['series']}*\n\n"
            f"⏳ **Priority:** {user.mention} has **5 minutes of exclusive drop priority**!\n"
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

@bot.tree.command(name="drop", description="Drops 3 random Anime Cards from your local character DB (15m Cooldown)")
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

async def process_inventory(ctx_or_interaction, tag_filter: str = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    rows = get_user_inventory(user.id, tag_filter)

    title_suffix = f" (Tag: [{tag_filter}])" if tag_filter else ""

    if not rows:
        msg = f"Coo coo! 🎴 No cards found in your collection{title_suffix}! Type `/drop` to start collecting!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    embed = discord.Embed(
        title=f"🎴 {user.display_name}'s Card Collection{title_suffix}",
        description=f"Total Cards: **{len(rows)}**",
        color=discord.Color.purple()
    )

    for row in rows[:10]:
        card_id, code, char_name, series, rarity, mint_num, edition, img_url, tag_val = row
        code_str = code if code else f"c{card_id:04d}"
        ed_val = edition if edition else 1
        tag_disp = f" 🏷️ `[{tag_val}]`" if tag_val else ""
        embed.add_field(
            name=f"🆔 Card ID: `{code_str}` • {char_name}{tag_disp}",
            value=f"Edition {ed_val} • Print #{mint_num} | 📺 *{series}* | {rarity}",
            inline=False
        )

    if len(rows) > 10:
        embed.set_footer(text=f"Showing 10 of {len(rows)} cards. Type /card code:<code> to see full card artwork!")
    else:
        embed.set_footer(text="Type /card code:<code> to see full card artwork!")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="inventory", description="View your collected Anime Cards (Optional tag filter)")
async def inventory_slash(interaction: discord.Interaction, tag: str = None):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await process_inventory(interaction, tag)

@bot.command(name="inventory")
async def inventory_prefix(ctx, *, tag: str = None):
    await process_inventory(ctx, tag)

@bot.command(name="i")
async def inventory_prefix_i(ctx, *, tag: str = None):
    await process_inventory(ctx, tag)

@bot.command(name="inv")
async def inventory_prefix_inv(ctx, *, tag: str = None):
    await process_inventory(ctx, tag)

async def process_view_card(ctx_or_interaction, card_code_query: str = None):
    user = ctx_or_interaction.user if isinstance(ctx_or_interaction, discord.Interaction) else ctx_or_interaction.author
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()

    if not card_code_query:
        cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, grabbed_at FROM inventory WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user.id,))
        row = cursor.fetchone()
    else:
        query_str = card_code_query.lower().strip()
        cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, image_url, tag, grabbed_at FROM inventory WHERE (code = ? OR id = ?) AND user_id = ?", (query_str, query_str, user.id))
        row = cursor.fetchone()

        if not row:
            cursor.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ? AND LOWER(tag) = ?", (user.id, query_str))
            tag_count = cursor.fetchone()[0]
            if tag_count > 0:
                conn.close()
                await process_inventory(ctx_or_interaction, tag_filter=query_str)
                return

    if not row:
        conn.close()
        if not card_code_query:
            msg = "Coo coo! ⚠️ You don't have any cards in your inventory yet! Type `/drop` to grab your first card!"
        else:
            msg = f"Coo coo! ⚠️ Card ID or Tag `{card_code_query}` not found in your inventory!"
            
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)
        return

    cid, code, uid, char_name, series, rarity, mint_num, edition, img_url, tag_val, grabbed_at = row
    conn.close()

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

    tag_disp = f"🏷️ **Tag:** `[{tag_val}]`\n" if tag_val else ""

    embed = discord.Embed(
        title=f"🆔 Card ID: {code_str} • {char_name}",
        description=(
            f"📺 **Series:** {series}\n"
            f"👤 **Owner:** {owner_name}\n"
            f"{tag_disp}"
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

@bot.tree.command(name="trade", description="Initiates a Karuta-style card/gems trade with another player")
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
async def trade_add_prefix(ctx, code_or_gems: str):
    if ctx.channel.id not in ACTIVE_TRADES:
        await ctx.send("Coo coo! ⚠️ There is no active trade session in this channel!")
        return
    session = ACTIVE_TRADES[ctx.channel.id]
    if ctx.author.id not in [session.p1.id, session.p2.id]:
        await ctx.send("Coo coo! ⚠️ You are not part of the active trade in this channel!")
        return
    
    val = code_or_gems.lower().strip()
    if val.endswith("g") or val.endswith("gems") or val.isdigit():
        clean_num = val.rstrip("gems").rstrip("g").strip()
        if clean_num.isdigit():
            await session.set_gems(ctx, int(clean_num))
            return
    await session.add_card(ctx, code_or_gems)

@bot.command(name="tr")
async def trade_remove_prefix(ctx, code_or_gems: str):
    if ctx.channel.id not in ACTIVE_TRADES:
        await ctx.send("Coo coo! ⚠️ There is no active trade session in this channel!")
        return
    session = ACTIVE_TRADES[ctx.channel.id]
    if ctx.author.id not in [session.p1.id, session.p2.id]:
        await ctx.send("Coo coo! ⚠️ You are not part of the active trade in this channel!")
        return

    val = code_or_gems.lower().strip()
    if val in ["gems", "gem", "g"]:
        await session.set_gems(ctx, 0)
        return
    await session.remove_card(ctx, code_or_gems)

# ==========================================
# 📖 COMPREHENSIVE HELP EMBED SYSTEM
# ==========================================
async def send_help_menu(ctx_or_interaction):
    embed = discord.Embed(
        title="🐦 Coo Coo Bot — Official Command & Rule Guide",
        description="Welcome to Coo Coo! Below is a complete list of commands, shortcuts, and card mechanics.",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="⏱️ Command Cooldowns",
        value=(
            "• **`!cd`** or **`/cd`** — Check your Drop (15m), Grab (5m), and Daily (24h) timers!\n"
            "• **`🎴 Drop Cooldown`** — 15 minutes per user.\n"
            "• **`🖐️ Grab Cooldown`** — 5 minutes per user.\n"
            "• **`🔒 Priority Window`** — Dropper has 5 minutes of exclusive grab priority."
        ),
        inline=False
    )

    embed.add_field(
        name="💎 Gems & 🧪 Dust Economy",
        value=(
            "• **`!bal`** or **`/bal`** — Check your personal Gem balance (Private!).\n"
            "• **`!dust`** or **`/dust`** — Check your Dust flask balance.\n"
            "• **`!daily`** or **`/daily`** — Claim 500 free Gems every 24 hours!\n"
            "• **`!pay @user <amt>`** or **`/pay`** — Transfer Gems to a friend."
        ),
        inline=False
    )

    embed.add_field(
        name="🔥 Burning & 🏷️ Tagging",
        value=(
            "• **`!burn <id>`** or **`/burn`** — Burn an unwanted card for Dust (Prompts for Epic+!).\n"
            "• **`!tag <id> <name>`** or **`/tag`** — Assign a folder tag to a card.\n"
            "• **`!untag <id>`** or **`/untag`** — Remove a tag from a card.\n"
            "• **`!viewtag <tag>`** or **`!vt <tag>`** or **`!inv <tag>`** — View all cards in a tag folder!"
        ),
        inline=False
    )

    embed.add_field(
        name="🎴 Card Drops & Collecting",
        value=(
            "• **`!d`** or **`!drop`** or **`/drop`** — Drops 3 random anime cards (15m CD).\n"
            "• **`1️⃣ 2️⃣ 3️⃣ Buttons`** — Grab cards (5m dropper priority!).\n"
            "• **`!v`** or **`!v <id>`** or **`/card`** — View high-res card artwork.\n"
            "• **`!i`** or **`!inv`** or **`/inventory`** — Open your card binder collection."
        ),
        inline=False
    )

    embed.add_field(
        name="🤝 Card & Gems Trading",
        value=(
            "• **`!t @user`** or **`!trade @user`** or **`/trade`** — Start a trade.\n"
            "• **`!ta <id>`** or **`!ta 250g`** — Add a card or Gems to trade offer.\n"
            "• **`!tr <id>`** or **`!tr gems`** — Remove a card or reset Gems.\n"
            "• **Buttons (`➕` `➖` `✅` `❌`)** — Manage trade & confirm."
        ),
        inline=False
    )

    embed.add_field(
        name="👑 Card Rarities & Burn Yields",
        value=(
            "• **`✨ Legendary` (Gold Frame)** — **1% Drop Rate** | Burns to **+200 🧪 Dust**\n"
            "• **`🟣 Epic` (Purple Frame)** — **8% Drop Rate** | Burns to **+100 🧪 Dust**\n"
            "• **`🔷 Rare` (Cyan Frame)** — **15% Drop Rate** | Burns to **+50 🧪 Dust**\n"
            "• **`⚪ Common` (Silver Frame)** — **76% Drop Rate** | Burns to **+20 🧪 Dust**"
        ),
        inline=False
    )

    embed.add_field(
        name="🎨 Server Utilities & Pigeon Wisdom",
        value=(
            "• **`!setup-colors`** or **`/setup-colors`** — Custom name color menu.\n"
            "• **`!coo`** or **`/coo`** — Pigeon wisdom from NYC sidewalk!"
        ),
        inline=False
    )

    embed.set_footer(text="Coo Coo Bot • Anime Card, Tagging & Dusting Engine")

    if isinstance(ctx_or_interaction, discord.Interaction):
        await ctx_or_interaction.followup.send(embed=embed)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="help", description="Displays Coo Coo's official command and rules guide")
async def help_slash(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
    except Exception:
        pass
    await send_help_menu(interaction)

@bot.command(name="help")
async def help_prefix(ctx):
    await send_help_menu(ctx)

@bot.command(name="h")
async def help_prefix_h(ctx):
    await send_help_menu(ctx)

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
    await interaction.followup.send(f"🐦 **Coo Coo**: {msg}")

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ Error: Please put your Discord Bot Token in the .env file!")
    else:
        bot.run(TOKEN)
