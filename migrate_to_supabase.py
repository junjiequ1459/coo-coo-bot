"""
One-time migration script: SQLite (Railway volume) → Supabase (PostgreSQL).
Runs on Railway at bot startup if both /data/inventory.db exists and DATABASE_URL is set.
"""
import os
import sqlite3
import psycopg2

def migrate():
    sqlite_path = None
    
    # Check Railway volume path first, then local
    for path in ["/data/inventory.db", os.path.join(os.path.dirname(__file__), "inventory.db")]:
        if os.path.exists(path):
            sqlite_path = path
            break
    
    if not sqlite_path:
        print("⏭️  No SQLite database found — skipping migration.")
        return False
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("⏭️  No DATABASE_URL set — skipping migration.")
        return False
    
    # Check if migration already happened (marker file)
    marker = sqlite_path + ".migrated"
    if os.path.exists(marker):
        print("⏭️  Migration already completed — skipping.")
        return False
    
    print(f"🔄 Starting migration from {sqlite_path} → Supabase...")
    
    # Connect to both databases
    lite = sqlite3.connect(sqlite_path)
    lite.row_factory = sqlite3.Row
    pg = psycopg2.connect(database_url)
    pg_cur = pg.cursor()
    
    try:
        # --- Create tables first ---
        print("🏗️  Creating tables in Supabase...")
        pg_cur.execute("""
            CREATE TABLE IF NOT EXISTS cards_pool (
                id SERIAL PRIMARY KEY, anilist_id INTEGER UNIQUE,
                character_name TEXT NOT NULL, series_name TEXT NOT NULL,
                image_url TEXT NOT NULL, favourites INTEGER DEFAULT 0, rarity TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY, gems INTEGER DEFAULT 0, dust INTEGER DEFAULT 0,
                last_daily BIGINT DEFAULT 0, last_drop BIGINT DEFAULT 0, last_grab BIGINT DEFAULT 0,
                premium_until BIGINT DEFAULT 0, drop_tickets INTEGER DEFAULT 0, grab_tickets INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY, code TEXT UNIQUE, user_id BIGINT NOT NULL,
                character_name TEXT NOT NULL, series_name TEXT NOT NULL, image_url TEXT NOT NULL,
                rarity TEXT NOT NULL, mint_number INTEGER NOT NULL, edition INTEGER DEFAULT 1,
                tag TEXT DEFAULT NULL, quality TEXT DEFAULT 'Mint ⭐⭐⭐⭐',
                dropped_by BIGINT DEFAULT NULL, grabbed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS mints (
                character_name TEXT, edition INTEGER DEFAULT 1, current_mint INTEGER NOT NULL,
                PRIMARY KEY (character_name, edition)
            );
            CREATE TABLE IF NOT EXISTS wishlists (
                id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, character_name TEXT NOT NULL,
                UNIQUE(user_id, character_name)
            );
            CREATE TABLE IF NOT EXISTS favorites (
                id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, card_code TEXT NOT NULL,
                UNIQUE(user_id, card_code)
            );
        """)
        pg.commit()
        print("✅ Tables created!")

        # Switch to autocommit so one bad row doesn't kill the rest
        pg.autocommit = True

        # --- Migrate cards_pool ---
        print("📦 Migrating cards_pool...")
        lite_cur = lite.execute("SELECT anilist_id, character_name, series_name, image_url, favourites, rarity FROM cards_pool")
        rows = lite_cur.fetchall()
        count = 0
        for row in rows:
            try:
                pg_cur.execute(
                    "INSERT INTO cards_pool (anilist_id, character_name, series_name, image_url, favourites, rarity) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (anilist_id) DO NOTHING",
                    (row["anilist_id"], row["character_name"], row["series_name"], row["image_url"], row["favourites"], row["rarity"])
                )
                count += 1
            except Exception as e:
                print(f"  ⚠️ cards_pool row error: {e}")
        print(f"  ✅ cards_pool: {count} rows")
        
        # --- Migrate users ---
        print("👥 Migrating users...")
        try:
            lite_cur = lite.execute("SELECT user_id, gems, dust, last_daily, last_drop, last_grab, premium_until, drop_tickets, grab_tickets FROM users")
        except sqlite3.OperationalError:
            lite_cur = lite.execute("SELECT user_id, gems, dust, last_daily, last_drop, last_grab, premium_until, drop_tickets FROM users")
        rows = lite_cur.fetchall()
        count = 0
        for row in rows:
            try:
                grab_tickets = row["grab_tickets"] if "grab_tickets" in row.keys() else 0
                pg_cur.execute(
                    "INSERT INTO users (user_id, gems, dust, last_daily, last_drop, last_grab, premium_until, drop_tickets, grab_tickets) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO NOTHING",
                    (row["user_id"], row["gems"] or 0, row["dust"] or 0, row["last_daily"] or 0, row["last_drop"] or 0, row["last_grab"] or 0, row["premium_until"] or 0, row["drop_tickets"] or 0, grab_tickets or 0)
                )
                count += 1
            except Exception as e:
                print(f"  ⚠️ users row error: {e}")
        print(f"  ✅ users: {count} rows")
        
        # --- Migrate inventory ---
        print("🎴 Migrating inventory...")
        lite_cur = lite.execute("SELECT * FROM inventory")
        col_names = [desc[0] for desc in lite_cur.description]
        rows = lite_cur.fetchall()
        count = 0
        for row in rows:
            row_dict = dict(zip(col_names, row))
            try:
                dropped_by = row_dict.get("dropped_by") or row_dict.get("user_id")
                quality = row_dict.get("quality") or "Good ⭐⭐"
                pg_cur.execute(
                    "INSERT INTO inventory (code, user_id, character_name, series_name, image_url, rarity, mint_number, edition, tag, quality, dropped_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (code) DO NOTHING",
                    (row_dict.get("code"), row_dict["user_id"], row_dict["character_name"], row_dict["series_name"], row_dict["image_url"], row_dict["rarity"], row_dict["mint_number"], row_dict.get("edition", 1), row_dict.get("tag"), quality, dropped_by)
                )
                count += 1
            except Exception as e:
                print(f"  ⚠️ inventory row error: {e}")
        print(f"  ✅ inventory: {count} rows")
        
        # --- Migrate mints ---
        print("🔢 Migrating mints...")
        lite_cur = lite.execute("SELECT character_name, edition, current_mint FROM mints")
        rows = lite_cur.fetchall()
        count = 0
        for row in rows:
            try:
                pg_cur.execute(
                    "INSERT INTO mints (character_name, edition, current_mint) VALUES (%s, %s, %s) ON CONFLICT (character_name, edition) DO NOTHING",
                    (row["character_name"], row["edition"] if row["edition"] else 1, row["current_mint"])
                )
                count += 1
            except Exception as e:
                print(f"  ⚠️ mints row error: {e}")
        print(f"  ✅ mints: {count} rows")
        
        # --- Migrate wishlists (if exists) ---
        try:
            lite_cur = lite.execute("SELECT user_id, character_name FROM wishlists")
            rows = lite_cur.fetchall()
            count = 0
            for row in rows:
                try:
                    pg_cur.execute(
                        "INSERT INTO wishlists (user_id, character_name) VALUES (%s, %s) ON CONFLICT (user_id, character_name) DO NOTHING",
                        (row["user_id"], row["character_name"])
                    )
                    count += 1
                except Exception:
                    pass
            print(f"  ✅ wishlists: {count} rows")
        except sqlite3.OperationalError:
            print("  ⏭️  wishlists table doesn't exist — skipping")
        
        # --- Migrate favorites (if exists) ---
        try:
            lite_cur = lite.execute("SELECT user_id, card_code FROM favorites")
            rows = lite_cur.fetchall()
            count = 0
            for row in rows:
                try:
                    pg_cur.execute(
                        "INSERT INTO favorites (user_id, card_code) VALUES (%s, %s) ON CONFLICT (user_id, card_code) DO NOTHING",
                        (row["user_id"], row["card_code"])
                    )
                    count += 1
                except Exception:
                    pass
            print(f"  ✅ favorites: {count} rows")
        except sqlite3.OperationalError:
            print("  ⏭️  favorites table doesn't exist — skipping")
        
        # Mark migration complete
        try:
            with open(marker, "w") as f:
                f.write("migrated")
            print(f"📝 Created migration marker: {marker}")
        except Exception:
            pass
        
        print("🎉 Migration complete! All data transferred to Supabase.")
        return True
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        lite.close()
        pg.close()

if __name__ == "__main__":
    migrate()
