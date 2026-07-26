from db import get_connection, release_connection


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
        frame TEXT NOT NULL DEFAULT 'default',
        tag TEXT DEFAULT NULL,
        quality TEXT DEFAULT 'Mint ⭐⭐⭐⭐',
        dropped_by BIGINT DEFAULT NULL,
        grabbed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Keep existing Supabase inventories compatible with the frame system.
    cursor.execute("ALTER TABLE inventory ADD COLUMN IF NOT EXISTS frame TEXT")
    cursor.execute(
        "UPDATE inventory SET frame = 'default' "
        "WHERE frame IS NULL OR BTRIM(frame) = ''"
    )
    cursor.execute(
        "ALTER TABLE inventory ALTER COLUMN frame SET DEFAULT 'default'"
    )
    cursor.execute("ALTER TABLE inventory ALTER COLUMN frame SET NOT NULL")

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
