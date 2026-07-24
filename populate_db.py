import sqlite3
import aiohttp
import asyncio
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")
ANILIST_URL = "https://graphql.anilist.co"

ANILIST_QUERY = """query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      hasNextPage
    }
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

async def populate_cards_pool(max_pages: int = 30):
    init_pool_table()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"📦 Starting AniList DB Population (Target: Top {max_pages * 50} Characters)...")

    total_inserted = 0
    async with aiohttp.ClientSession() as session:
        for page in range(1, max_pages + 1):
            variables = {"page": page, "perPage": 50}
            try:
                async with session.post(ANILIST_URL, json={"query": ANILIST_QUERY, "variables": variables}, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        char_list = data["data"]["Page"]["characters"]
                        for char in char_list:
                            anilist_id = char["id"]
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

                            cursor.execute("""
                            INSERT OR REPLACE INTO cards_pool (anilist_id, character_name, series_name, image_url, favourites, rarity)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """, (anilist_id, char_name, series, img_url, favs, rarity))
                            total_inserted += 1

                        conn.commit()
                        print(f"  [Page {page}/{max_pages}] Processed 50 characters (Total: {total_inserted}).")
                    else:
                        print(f"  [Page {page}] HTTP {resp.status}. Waiting 5 seconds...")
                        await asyncio.sleep(5)
            except Exception as e:
                print(f"  [Page {page}] Error: {e}")

            await asyncio.sleep(0.4)

    cursor.execute("SELECT COUNT(*) FROM cards_pool")
    count = cursor.fetchone()[0]
    conn.close()
    print(f"✅ Population Complete! Total Cards in DB Pool: {count:,}")

if __name__ == "__main__":
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    asyncio.run(populate_cards_pool(pages))
