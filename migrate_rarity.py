"""
One-time migration script to:
1. Strip emojis from existing rarity values in cards_pool and inventory
2. Reclassify cards_pool rarity based on favourites thresholds
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # === Step 1: Strip emojis from cards_pool ===
    print("🔄 Step 1: Stripping emojis from cards_pool rarity values...")
    emoji_map = [
        ("✨ Legendary", "Legendary"),
        ("🟣 Epic", "Epic"),
        ("🔷 Rare", "Rare"),
        ("⚪ Common", "Common"),
    ]
    for old, new in emoji_map:
        cursor.execute("UPDATE cards_pool SET rarity = %s WHERE rarity = %s", (new, old))
        print(f"  cards_pool: '{old}' → '{new}': {cursor.rowcount} rows")

    # === Step 2: Strip emojis from inventory ===
    print("\n🔄 Step 2: Stripping emojis from inventory rarity values...")
    for old, new in emoji_map:
        cursor.execute("UPDATE inventory SET rarity = %s WHERE rarity = %s", (new, old))
        print(f"  inventory: '{old}' → '{new}': {cursor.rowcount} rows")

    # === Step 3: Reclassify cards_pool by favourites (order matters: highest first) ===
    print("\n🔄 Step 3: Reclassifying cards_pool rarity by favourites thresholds...")

    cursor.execute("UPDATE cards_pool SET rarity = 'Mythic' WHERE favourites > 10000")
    print(f"  Mythic (favs > 10000): {cursor.rowcount} rows")

    cursor.execute("UPDATE cards_pool SET rarity = 'Legendary' WHERE favourites > 5000 AND favourites <= 10000")
    print(f"  Legendary (favs > 5000): {cursor.rowcount} rows")

    cursor.execute("UPDATE cards_pool SET rarity = 'Epic' WHERE favourites > 1000 AND favourites <= 5000")
    print(f"  Epic (favs > 1000): {cursor.rowcount} rows")

    cursor.execute("UPDATE cards_pool SET rarity = 'Rare' WHERE favourites > 500 AND favourites <= 1000")
    print(f"  Rare (favs > 500): {cursor.rowcount} rows")

    cursor.execute("UPDATE cards_pool SET rarity = 'Common' WHERE favourites <= 500")
    print(f"  Common (favs <= 500): {cursor.rowcount} rows")

    # === Summary ===
    print("\n📊 Final cards_pool distribution:")
    cursor.execute("SELECT rarity, COUNT(*) FROM cards_pool GROUP BY rarity ORDER BY COUNT(*) DESC")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} cards")

    print("\n📊 Final inventory distribution:")
    cursor.execute("SELECT rarity, COUNT(*) FROM inventory GROUP BY rarity ORDER BY COUNT(*) DESC")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} cards")

    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    migrate()
