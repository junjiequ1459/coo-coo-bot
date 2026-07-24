import sqlite3
import aiohttp
import asyncio
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")
ANILIST_URL = "https://graphql.anilist.co"

ANILIST_QUERY = """query ($page: Int, $perPage: Int, $sort: [CharacterSort]) {
  Page(page: $page, perPage: $perPage) {
    characters(sort: $sort) {
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

def init_pool_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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

async def populate_cards_pool(target_count: int = 10000):
    init_pool_table()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cards_pool")
    current_count = cursor.fetchone()[0]
    conn.close()

    print(f"📦 Current DB Pool: {current_count:,} characters. Target: {target_count:,} characters.")
    if current_count >= target_count:
        print("✅ Already reached target!")
        return

    async with aiohttp.ClientSession() as session:
        sort_modes = [["FAVOURITES_DESC"], ["ID_DESC"], ["RELEVANCE"]]
        
        for sort_mode in sort_modes:
            for page in range(1, 300):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM cards_pool")
                curr = cursor.fetchone()[0]
                if curr >= target_count:
                    conn.close()
                    print(f"🎉 Reached target of {target_count:,} characters!")
                    return

                variables = {"page": page, "perPage": 50, "sort": sort_mode}
                try:
                    async with session.post(ANILIST_URL, json={"query": ANILIST_QUERY, "variables": variables}, timeout=15) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            char_list = data["data"]["Page"]["characters"]
                            if not char_list:
                                conn.close()
                                break
                            
                            for char in char_list:
                                anilist_id = char["id"]
                                char_name = char.get("name", {}).get("full")
                                if not char_name:
                                    continue
                                
                                img_url = char.get("image", {}).get("large")
                                if not img_url or "default.jpg" in img_url:
                                    continue

                                favs = char.get("favourites", 0) or 0
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

                                cursor.execute("""
                                INSERT OR IGNORE INTO cards_pool (anilist_id, character_name, series_name, image_url, favourites, rarity)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """, (anilist_id, char_name, series, img_url, favs, rarity))

                            conn.commit()
                            cursor.execute("SELECT COUNT(*) FROM cards_pool")
                            new_curr = cursor.fetchone()[0]
                            conn.close()
                            print(f"  [Sort {sort_mode[0]} | Page {page}] Total pool: {new_curr:,} / {target_count:,}")
                        else:
                            conn.close()
                            print(f"  HTTP {resp.status}, waiting 5s...")
                            await asyncio.sleep(5)
                except Exception as e:
                    conn.close()
                    print(f"  Error page {page}: {e}")

                await asyncio.sleep(0.35)

if __name__ == "__main__":
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    asyncio.run(populate_cards_pool(target))
