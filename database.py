import sqlite3
import random
import string
import time
from config import DB_PATH, RARITY_WEIGHTS

def generate_card_code() -> str:
    """Generates a random 6-character alphanumeric card code (e.g. 136hma)."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=6))

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
    if "quality" not in inv_columns:
        cursor.execute("ALTER TABLE inventory ADD COLUMN quality TEXT DEFAULT 'Mint ⭐⭐⭐⭐'")
        cursor.execute("UPDATE inventory SET quality = 'Mint ⭐⭐⭐⭐'")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mints (
        character_name TEXT PRIMARY KEY,
        current_mint INTEGER NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        gems INTEGER DEFAULT 0,
        dust INTEGER DEFAULT 0,
        last_daily INTEGER DEFAULT 0,
        last_drop INTEGER DEFAULT 0,
        last_grab INTEGER DEFAULT 0,
        premium_until INTEGER DEFAULT 0,
        drop_tickets INTEGER DEFAULT 0
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
    if "premium_until" not in usr_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN premium_until INTEGER DEFAULT 0")
    if "drop_tickets" not in usr_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN drop_tickets INTEGER DEFAULT 0")
    if "grab_tickets" not in usr_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN grab_tickets INTEGER DEFAULT 0")

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
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, 0, 0)", (user_id,))
        conn.commit()
        gems = 0
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
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, 0, 0)", (user_id,))
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
        new_gems = max(0, amount)
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
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, 0, ?)", (user_id, new_dust))
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

        cursor.execute("UPDATE users SET gems = gems - ? WHERE user_id = ?", (amount, from_user_id))

        cursor.execute("SELECT gems FROM users WHERE user_id = ?", (to_user_id,))
        row2 = cursor.fetchone()
        if not row2:
            cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, ?, 0)", (to_user_id, amount))
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

def save_card_to_inventory(user_id: int, code: str, character_name: str, series_name: str, image_url: str, rarity: str, mint_number: int, edition: int = 1, quality: str = None) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    q_final = quality if quality else "Mint ⭐⭐⭐⭐"
    cursor.execute("""
    INSERT INTO inventory (user_id, code, character_name, series_name, image_url, rarity, mint_number, edition, quality)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, code, character_name, series_name, image_url, rarity, mint_number, edition, q_final))
    inserted_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inserted_id

def get_user_inventory(user_id: int, tag_filter: str = None):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    if tag_filter:
        cursor.execute("SELECT id, code, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality FROM inventory WHERE user_id = ? AND LOWER(tag) = ? ORDER BY id DESC", (user_id, tag_filter.lower().strip()))
    else:
        cursor.execute("SELECT id, code, character_name, series_name, rarity, mint_number, edition, image_url, tag, quality FROM inventory WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_card_by_code_and_owner(code: str, user_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, user_id, character_name, series_name, rarity, mint_number, edition, tag, quality FROM inventory WHERE (code = ? OR id = ?) AND user_id = ?", (code.lower().strip(), code.strip(), user_id))
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

def update_card_quality(code_str: str, user_id: int, new_quality: str) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    query_str = code_str.lower().strip()
    cursor.execute("UPDATE inventory SET quality = ? WHERE (code = ? OR id = ?) AND user_id = ?", (new_quality, query_str, query_str, user_id))
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
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (?, 0, 0)", (user_id,))
    
    if cd_type == "drop":
        cursor.execute("UPDATE users SET last_drop = ? WHERE user_id = ?", (ts, user_id))
    elif cd_type == "grab":
        cursor.execute("UPDATE users SET last_grab = ? WHERE user_id = ?", (ts, user_id))
    elif cd_type == "daily":
        cursor.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (ts, user_id))
    conn.commit()
    conn.close()

def get_user_premium_until(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT premium_until FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        return 0
    return row[0]

def is_user_premium(user_id: int) -> bool:
    prem_until = get_user_premium_until(user_id)
    return int(time.time()) < prem_until

def add_user_premium(user_id: int, days: int = 30) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    now = int(time.time())
    curr_until = get_user_premium_until(user_id)
    
    start_base = max(now, curr_until)
    new_until = start_base + (days * 86400)
    
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, gems, dust, premium_until) VALUES (?, 0, 0, ?)", (user_id, new_until))
    else:
        cursor.execute("UPDATE users SET premium_until = ? WHERE user_id = ?", (new_until, user_id))
        
    conn.commit()
    conn.close()
    return new_until

def get_effective_cooldowns(user_id: int):
    """Returns (drop_cd_sec, grab_cd_sec) based on whether user has active Premium Pass."""
    if is_user_premium(user_id):
        return 450, 150  # 7.5 Minutes Drop CD, 2.5 Minutes Grab CD
    return 900, 300      # 15 Minutes Drop CD, 5 Minutes Grab CD

def get_user_drop_tickets(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT drop_tickets FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        return 0
    return row[0]

def add_user_drop_tickets(user_id: int, amount: int) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    curr = get_user_drop_tickets(user_id)
    new_val = max(0, curr + amount)
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, gems, dust, drop_tickets) VALUES (?, 0, 0, ?)", (user_id, new_val))
    else:
        cursor.execute("UPDATE users SET drop_tickets = ? WHERE user_id = ?", (new_val, user_id))
    conn.commit()
    conn.close()
    return new_val

def get_user_grab_tickets(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT grab_tickets FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        return 0
    return row[0]

def add_user_grab_tickets(user_id: int, amount: int) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    curr = get_user_grab_tickets(user_id)
    new_val = max(0, curr + amount)
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, gems, dust, grab_tickets) VALUES (?, 0, 0, ?)", (user_id, new_val))
    else:
        cursor.execute("UPDATE users SET grab_tickets = ? WHERE user_id = ?", (new_val, user_id))
    conn.commit()
    conn.close()
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
                "quality": roll_card_quality(),
                "temp_mint": temp_mint,
                "edition": 1
            })

    conn.close()
    return cards
