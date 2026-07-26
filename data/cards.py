import random
import string

from config import RARITY_WEIGHTS
from db import get_connection, release_connection


def generate_card_code() -> str:
    """Generates a random 6-character alphanumeric card code (e.g. 136hma)."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=6))

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

def save_card_to_inventory(
    user_id: int,
    code: str,
    character_name: str,
    series_name: str,
    image_url: str,
    rarity: str,
    mint_number: int,
    edition: int = 1,
    quality: str = None,
    dropped_by: int = None,
    frame: str = "default",
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    q_final = quality if quality else "Mint ⭐⭐⭐⭐"
    dropper = dropped_by if dropped_by else user_id
    frame_name = str(frame or "default").strip().lower() or "default"
    cursor.execute("""
    INSERT INTO inventory (
        user_id, code, character_name, series_name, image_url, rarity,
        mint_number, edition, quality, dropped_by, frame
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """, (
        user_id,
        code,
        character_name,
        series_name,
        image_url,
        rarity,
        mint_number,
        edition,
        q_final,
        dropper,
        frame_name,
    ))
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
    query_str = str(code_str).lower().strip()
    raw_id = query_str[1:] if (query_str.startswith('c') and query_str[1:].isdigit()) else query_str
    cursor.execute("UPDATE inventory SET quality = %s WHERE (code = %s OR CAST(id AS TEXT) = %s OR CAST(id AS TEXT) = %s) AND user_id = %s", (new_quality, query_str, query_str, raw_id, user_id))
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
