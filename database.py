import random
import string
import time
from config import RARITY_WEIGHTS
from db import get_connection, release_connection

def generate_card_code() -> str:
    """Generates a random 6-character alphanumeric card code (e.g. 136hma)."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=6))

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id SERIAL PRIMARY KEY,
        code TEXT UNIQUE,
        user_id BIGINT NOT NULL,
        character_name TEXT NOT NULL,
        series_name TEXT NOT NULL,
        image_url TEXT NOT NULL,
        rarity TEXT NOT NULL,
        mint_number INTEGER NOT NULL,
        edition INTEGER DEFAULT 1,
        tag TEXT DEFAULT NULL,
        quality TEXT DEFAULT 'Mint ⭐⭐⭐⭐',
        dropped_by BIGINT DEFAULT NULL,
        grabbed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mints (
        character_name TEXT,
        edition INTEGER DEFAULT 1,
        current_mint INTEGER NOT NULL,
        PRIMARY KEY (character_name, edition)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        gems INTEGER DEFAULT 0,
        dust INTEGER DEFAULT 0,
        last_daily BIGINT DEFAULT 0,
        last_drop BIGINT DEFAULT 0,
        last_grab BIGINT DEFAULT 0,
        premium_until BIGINT DEFAULT 0,
        drop_tickets INTEGER DEFAULT 0,
        grab_tickets INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cards_pool (
        id SERIAL PRIMARY KEY,
        anilist_id INTEGER UNIQUE,
        character_name TEXT NOT NULL,
        series_name TEXT NOT NULL,
        image_url TEXT NOT NULL,
        favourites INTEGER DEFAULT 0,
        rarity TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wishlists (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        character_name TEXT NOT NULL,
        UNIQUE(user_id, character_name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        card_code TEXT NOT NULL,
        UNIQUE(user_id, card_code)
    )
    """)
    
    conn.commit()
    release_connection(conn)

init_db()

def get_user_gems(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT gems FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, 0, 0)", (user_id,))
        conn.commit()
        gems = 0
    else:
        gems = row[0]
    release_connection(conn)
    return gems

def get_user_dust(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dust FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, 0, 0)", (user_id,))
        conn.commit()
        dust = 0
    else:
        dust = row[0] if row[0] is not None else 0
    release_connection(conn)
    return dust

def add_user_gems(user_id: int, amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT gems FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        new_gems = max(0, amount)
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, %s, 0)", (user_id, new_gems))
    else:
        new_gems = row[0] + amount
        cursor.execute("UPDATE users SET gems = %s WHERE user_id = %s", (new_gems, user_id))
    conn.commit()
    release_connection(conn)
    return new_gems

def add_user_dust(user_id: int, amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dust FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        new_dust = amount
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, 0, %s)", (user_id, new_dust))
    else:
        curr = row[0] if row[0] is not None else 0
        new_dust = curr + amount
        cursor.execute("UPDATE users SET dust = %s WHERE user_id = %s", (new_dust, user_id))
    conn.commit()
    release_connection(conn)
    return new_dust

def transfer_gems(from_user_id: int, to_user_id: int, amount: int) -> bool:
    if amount <= 0:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT gems FROM users WHERE user_id = %s", (from_user_id,))
        row1 = cursor.fetchone()
        from_gems = row1[0] if row1 else 0

        if from_gems < amount:
            release_connection(conn)
            return False

        cursor.execute("UPDATE users SET gems = gems - %s WHERE user_id = %s", (amount, from_user_id))

        cursor.execute("SELECT gems FROM users WHERE user_id = %s", (to_user_id,))
        row2 = cursor.fetchone()
        if not row2:
            cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, %s, 0)", (to_user_id, amount))
        else:
            cursor.execute("UPDATE users SET gems = gems + %s WHERE user_id = %s", (amount, to_user_id))

        conn.commit()
        release_connection(conn)
        return True
    except Exception as e:
        print(f"Error transferring gems: {e}")
        conn.rollback()
        release_connection(conn)
        return False

def get_next_mint(character_name: str, edition: int = 1) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT current_mint FROM mints WHERE character_name = %s AND edition = %s", (character_name, edition))
    row = cursor.fetchone()
    if row:
        next_mint = row[0] + 1
        cursor.execute("UPDATE mints SET current_mint = %s WHERE character_name = %s AND edition = %s", (next_mint, character_name, edition))
    else:
        next_mint = 1
        cursor.execute("INSERT INTO mints (character_name, edition, current_mint) VALUES (%s, %s, %s)", (character_name, edition, next_mint))
    conn.commit()
    release_connection(conn)
    return next_mint

def save_card_to_inventory(user_id: int, code: str, character_name: str, series_name: str, image_url: str, rarity: str, mint_number: int, edition: int = 1, quality: str = None, dropped_by: int = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    q_final = quality if quality else "Mint ⭐⭐⭐⭐"
    dropper = dropped_by if dropped_by else user_id
    cursor.execute("""
    INSERT INTO inventory (user_id, code, character_name, series_name, image_url, rarity, mint_number, edition, quality, dropped_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """, (user_id, code, character_name, series_name, image_url, rarity, mint_number, edition, q_final, dropper))
    inserted_id = cursor.fetchone()[0]
    conn.commit()
    release_connection(conn)
    return inserted_id

def get_user_inventory(user_id: int, tag_filter: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    if tag_filter:
        cursor.execute("SELECT id, code, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality FROM inventory WHERE user_id = %s AND LOWER(tag) = %s ORDER BY id DESC", (user_id, tag_filter.lower().strip()))
    else:
        cursor.execute("SELECT id, code, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality FROM inventory WHERE user_id = %s ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    release_connection(conn)
    return rows

def get_card_by_code_and_owner(code: str, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, tag, quality FROM inventory WHERE (code = %s OR CAST(id AS TEXT) = %s) AND user_id = %s", (code.lower().strip(), code.strip(), user_id))
    row = cursor.fetchone()
    release_connection(conn)
    return row

def update_card_tag(code_str: str, user_id: int, tag_name: str = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    query_str = code_str.lower().strip()
    cursor.execute("UPDATE inventory SET tag = %s WHERE (code = %s OR CAST(id AS TEXT) = %s) AND user_id = %s", (tag_name, query_str, query_str, user_id))
    affected = cursor.rowcount
    conn.commit()
    release_connection(conn)
    return affected > 0

def update_card_quality(code_str: str, user_id: int, new_quality: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    query_str = code_str.lower().strip()
    cursor.execute("UPDATE inventory SET quality = %s WHERE (code = %s OR CAST(id AS TEXT) = %s) AND user_id = %s", (new_quality, query_str, query_str, user_id))
    affected = cursor.rowcount
    conn.commit()
    release_connection(conn)
    return affected > 0

def delete_card_from_inventory(code_str: str, user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    query_str = code_str.lower().strip()
    cursor.execute("SELECT id, code, character_name, rarity FROM inventory WHERE (code = %s OR CAST(id AS TEXT) = %s) AND user_id = %s", (query_str, query_str, user_id))
    row = cursor.fetchone()
    if not row:
        release_connection(conn)
        return None
    cursor.execute("DELETE FROM inventory WHERE id = %s", (row[0],))
    conn.commit()
    release_connection(conn)
    return row

def transfer_cards_between_users(user1_id: int, user1_codes: list, user2_id: int, user2_codes: list):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for code in user1_codes:
            cursor.execute("UPDATE inventory SET user_id = %s WHERE code = %s", (user2_id, code))
        for code in user2_codes:
            cursor.execute("UPDATE inventory SET user_id = %s WHERE code = %s", (user1_id, code))
        conn.commit()
        release_connection(conn)
        return True
    except Exception as e:
        print(f"Error transferring cards: {e}")
        conn.rollback()
        release_connection(conn)
        return False

def get_user_cooldowns(user_id: int):
    """Returns timestamps for last_drop, last_grab, last_daily."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_drop, last_grab, last_daily FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    release_connection(conn)
    if not row:
        return 0, 0, 0
    return (row[0] or 0), (row[1] or 0), (row[2] or 0)

def set_user_cooldown(user_id: int, cd_type: str, ts: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, 0, 0)", (user_id,))
    
    if cd_type == "drop":
        cursor.execute("UPDATE users SET last_drop = %s WHERE user_id = %s", (ts, user_id))
    elif cd_type == "grab":
        cursor.execute("UPDATE users SET last_grab = %s WHERE user_id = %s", (ts, user_id))
    elif cd_type == "daily":
        cursor.execute("UPDATE users SET last_daily = %s WHERE user_id = %s", (ts, user_id))
    conn.commit()
    release_connection(conn)

def get_user_premium_until(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT premium_until FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    release_connection(conn)
    if not row or not row[0]:
        return 0
    return row[0]

def is_user_premium(user_id: int) -> bool:
    prem_until = get_user_premium_until(user_id)
    return int(time.time()) < prem_until

def add_user_premium(user_id: int, days: int = 30) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = int(time.time())
    curr_until = get_user_premium_until(user_id)
    
    start_base = max(now, curr_until)
    new_until = start_base + (days * 86400)
    
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, gems, dust, premium_until) VALUES (%s, 0, 0, %s)", (user_id, new_until))
    else:
        cursor.execute("UPDATE users SET premium_until = %s WHERE user_id = %s", (new_until, user_id))
        
    conn.commit()
    release_connection(conn)
    return new_until

def get_effective_cooldowns(user_id: int):
    """Returns (drop_cd_sec, grab_cd_sec) based on whether user has active Premium Pass."""
    if is_user_premium(user_id):
        return 450, 150  # 7.5 Minutes Drop CD, 2.5 Minutes Grab CD
    return 900, 300      # 15 Minutes Drop CD, 5 Minutes Grab CD

def get_user_drop_tickets(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT drop_tickets FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    release_connection(conn)
    if not row or not row[0]:
        return 0
    return row[0]

def add_user_drop_tickets(user_id: int, amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    curr = get_user_drop_tickets(user_id)
    new_val = max(0, curr + amount)
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, gems, dust, drop_tickets) VALUES (%s, 0, 0, %s)", (user_id, new_val))
    else:
        cursor.execute("UPDATE users SET drop_tickets = %s WHERE user_id = %s", (new_val, user_id))
    conn.commit()
    release_connection(conn)
    return new_val

def get_user_grab_tickets(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT grab_tickets FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    release_connection(conn)
    if not row or not row[0]:
        return 0
    return row[0]

def add_user_grab_tickets(user_id: int, amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    curr = get_user_grab_tickets(user_id)
    new_val = max(0, curr + amount)
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, gems, dust, grab_tickets) VALUES (%s, 0, 0, %s)", (user_id, new_val))
    else:
        cursor.execute("UPDATE users SET grab_tickets = %s WHERE user_id = %s", (new_val, user_id))
    conn.commit()
    release_connection(conn)
    return new_val

QUALITY_WEIGHTS = [
    ("Mint ⭐⭐⭐⭐", 0.10),
    ("Excellent ⭐⭐⭐", 0.30),
    ("Good ⭐⭐", 0.40),
    ("Poor ⭐", 0.15),
    ("Damaged ❌", 0.05)
]

def roll_card_quality() -> str:
    qualities, weights = zip(*QUALITY_WEIGHTS)
    return random.choices(qualities, weights=weights, k=1)[0]

def sample_rarity() -> str:
    rarities, weights = zip(*RARITY_WEIGHTS)
    return random.choices(rarities, weights=weights, k=1)[0]

# --- In-memory card pool cache (loaded once, avoids network queries per drop) ---
_cards_cache = {}  # rarity -> list of (character_name, series_name, image_url, rarity)
_cards_all = []

def load_cards_cache():
    """Load the entire cards_pool table into memory, grouped by rarity."""
    global _cards_cache, _cards_all
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT character_name, series_name, image_url, rarity FROM cards_pool")
    rows = cursor.fetchall()
    release_connection(conn)

    _cards_cache = {}
    _cards_all = []
    for row in rows:
        char_name, series, img_url, rarity = row
        entry = (char_name, series, img_url, rarity)
        _cards_all.append(entry)
        if rarity not in _cards_cache:
            _cards_cache[rarity] = []
        _cards_cache[rarity].append(entry)
    
    print(f"📦 Loaded {len(_cards_all)} cards into memory cache ({len(_cards_cache)} rarities)")

# Load cache at startup
try:
    load_cards_cache()
except Exception as e:
    print(f"⚠️ Could not load cards cache: {e}")

def get_cards_from_db_pool(count: int = 3):
    """Fetches cards using weighted rarity probabilities from in-memory cache.
    Batches all mint lookups into a single DB connection for speed."""
    if not _cards_all:
        load_cards_cache()

    # Pick cards from memory (instant, no DB)
    picked = []
    for _ in range(count):
        target_rarity = sample_rarity()
        pool = _cards_cache.get(target_rarity, _cards_all)
        if not pool:
            pool = _cards_all
        picked.append(random.choice(pool))

    # Batch all mint lookups in ONE connection
    conn = get_connection()
    cursor = conn.cursor()
    cards = []
    for char_name, series, img_url, rarity in picked:
        cursor.execute("SELECT current_mint FROM mints WHERE character_name = %s AND edition = 1", (char_name,))
        row = cursor.fetchone()
        if row:
            next_mint = row[0] + 1
            cursor.execute("UPDATE mints SET current_mint = %s WHERE character_name = %s AND edition = 1", (next_mint, char_name))
        else:
            next_mint = 1
            cursor.execute("INSERT INTO mints (character_name, edition, current_mint) VALUES (%s, 1, 1)", (char_name,))

        cards.append({
            "code": generate_card_code(),
            "name": char_name,
            "series": series,
            "image": img_url,
            "rarity": rarity,
            "quality": roll_card_quality(),
            "temp_mint": next_mint,
            "edition": 1
        })
    conn.commit()
    release_connection(conn)

    return cards


