import sqlite3
import aiohttp
import asyncio
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")
ANILIST_URL = "https://graphql.anilist.co"

ANILIST_CHAR_QUERY = """
query ($search: String, $page: Int) {
  Page(page: $page, perPage: 50) {
    characters(search: $search) {
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
}
"""

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

async def fetch_hoyoverse_characters():
    init_pool_table()
    
    keywords = [
        "Genshin Impact", "Honkai", "Star Rail", "Zhongli", "Raiden", "Hu Tao", 
        "Acheron", "Kafka", "March 7th", "Firefly", "Furina", "Neuvillette", 
        "Arlecchino", "Kazuha", "Yae Miko", "Nahida", "Venti", "Diluc", "Keqing", 
        "Ganyu", "Ayaka", "Xiao", "Eula", "Itto", "Wriothesley", "Navia", "Clorinde",
        "Jing Liu", "Aventurine", "Blade", "Dan Heng", "Welt", "Bronya", "Seele", 
        "Tingyun", "Sparkle", "Ruan Mei", "Robin", "Sunday", "Bailu", "Fu Xuan"
    ]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    async with aiohttp.ClientSession() as session:
        for kw in keywords:
            print(f"🎮 Searching AniList for '{kw}' characters...")
            for page in range(1, 3):
                variables = {"search": kw, "page": page}
                try:
                    async with session.post(ANILIST_URL, json={"query": ANILIST_CHAR_QUERY, "variables": variables}, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            char_list = data.get("data", {}).get("Page", {}).get("characters", [])
                            if not char_list:
                                break
                            
                            for char in char_list:
                                c_id = char["id"]
                                c_name = char.get("name", {}).get("full")
                                if not c_name:
                                    continue
                                
                                img_url = char.get("image", {}).get("large")
                                if not img_url or "default.jpg" in img_url:
                                    continue

                                favs = char.get("favourites", 0) or 0
                                media_nodes = char.get("media", {}).get("nodes", [])
                                if media_nodes and media_nodes[0].get("title"):
                                    series = media_nodes[0]["title"].get("english") or media_nodes[0]["title"].get("romaji") or "Genshin Impact / Honkai"
                                else:
                                    series = "Genshin Impact / Honkai"

                                if favs >= 1000:
                                    rarity = "✨ Legendary"
                                elif favs >= 300:
                                    rarity = "🟣 Epic"
                                elif favs >= 50:
                                    rarity = "🔷 Rare"
                                else:
                                    rarity = "⚪ Common"

                                cursor.execute("""
                                INSERT OR IGNORE INTO cards_pool (anilist_id, character_name, series_name, image_url, favourites, rarity)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """, (c_id, c_name, series, img_url, favs, rarity))

                            conn.commit()
                except Exception as e:
                    print(f"Error querying '{kw}' page {page}: {e}")
                await asyncio.sleep(0.3)

    cursor.execute("SELECT COUNT(*) FROM cards_pool")
    pool_total = cursor.fetchone()[0]
    conn.close()
    print(f"✅ Successfully seeded Hoyoverse characters! Total cards in pool: {pool_total:,}")

if __name__ == "__main__":
    asyncio.run(fetch_hoyoverse_characters())
