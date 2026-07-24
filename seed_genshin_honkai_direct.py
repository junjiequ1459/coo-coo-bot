import sqlite3
import aiohttp
import asyncio
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")
ANILIST_URL = "https://graphql.anilist.co"

CHAR_SEARCH_QUERY = """
query ($name: String) {
  Character(search: $name) {
    id
    name {
      full
    }
    image {
      large
    }
    favourites
  }
}
"""

TARGET_CHARACTERS = [
    # Genshin Impact
    ("Raiden Shogun", "Genshin Impact", "✨ Legendary", 15000),
    ("Zhongli", "Genshin Impact", "✨ Legendary", 14500),
    ("Hu Tao", "Genshin Impact", "✨ Legendary", 14000),
    ("Furina", "Genshin Impact", "✨ Legendary", 13500),
    ("Neuvillette", "Genshin Impact", "✨ Legendary", 13000),
    ("Arlecchino", "Genshin Impact", "✨ Legendary", 12800),
    ("Kaedehara Kazuha", "Genshin Impact", "✨ Legendary", 12500),
    ("Yae Miko", "Genshin Impact", "🟣 Epic", 9500),
    ("Nahida", "Genshin Impact", "🟣 Epic", 9200),
    ("Venti", "Genshin Impact", "🟣 Epic", 8800),
    ("Diluc", "Genshin Impact", "🟣 Epic", 8500),
    ("Kamisato Ayaka", "Genshin Impact", "🟣 Epic", 8200),
    ("Xiao", "Genshin Impact", "🟣 Epic", 8000),
    ("Ganyu", "Genshin Impact", "🟣 Epic", 7800),
    ("Yelan", "Genshin Impact", "🟣 Epic", 7500),
    ("Navia", "Genshin Impact", "🟣 Epic", 7200),
    ("Clorinde", "Genshin Impact", "🟣 Epic", 6800),
    ("Wanderer", "Genshin Impact", "🟣 Epic", 6500),
    ("Tartaglia", "Genshin Impact", "🟣 Epic", 6200),
    ("Alhaitham", "Genshin Impact", "🟣 Epic", 6000),
    ("Keqing", "Genshin Impact", "🔷 Rare", 3800),
    ("Mona Megistus", "Genshin Impact", "🔷 Rare", 3500),
    ("Fischl", "Genshin Impact", "🔷 Rare", 3200),
    ("Bennett", "Genshin Impact", "🔷 Rare", 3000),
    ("Xiangling", "Genshin Impact", "🔷 Rare", 2800),
    ("Xingqiu", "Genshin Impact", "🔷 Rare", 2600),
    ("Paimon", "Genshin Impact", "⚪ Common", 900),
    ("Amber", "Genshin Impact", "⚪ Common", 800),
    ("Kaeya Alberich", "Genshin Impact", "⚪ Common", 750),
    ("Lisa Minci", "Genshin Impact", "⚪ Common", 700),
    ("Eula", "Genshin Impact", "🟣 Epic", 7000),
    ("Klee", "Genshin Impact", "🟣 Epic", 6500),
    ("Arataki Itto", "Genshin Impact", "🟣 Epic", 6200),
    ("Wriothesley", "Genshin Impact", "🟣 Epic", 6000),

    # Honkai: Star Rail
    ("Acheron", "Honkai: Star Rail", "✨ Legendary", 14000),
    ("Firefly", "Honkai: Star Rail", "✨ Legendary", 13800),
    ("Kafka", "Honkai: Star Rail", "✨ Legendary", 13500),
    ("Jingliu", "Honkai: Star Rail", "✨ Legendary", 12500),
    ("Aventurine", "Honkai: Star Rail", "🟣 Epic", 9800),
    ("Jing Yuan", "Honkai: Star Rail", "🟣 Epic", 9500),
    ("Blade", "Honkai: Star Rail", "🟣 Epic", 9000),
    ("Dan Heng", "Honkai: Star Rail", "🟣 Epic", 8800),
    ("Sparkle", "Honkai: Star Rail", "🟣 Epic", 8500),
    ("Ruan Mei", "Honkai: Star Rail", "🟣 Epic", 8200),
    ("Robin", "Honkai: Star Rail", "🟣 Epic", 8000),
    ("Feixiao", "Honkai: Star Rail", "🟣 Epic", 7800),
    ("Black Swan", "Honkai: Star Rail", "🟣 Epic", 7500),
    ("Topaz", "Honkai: Star Rail", "🟣 Epic", 7000),
    ("Bronya Rand", "Honkai: Star Rail", "🔷 Rare", 3900),
    ("Seele", "Honkai: Star Rail", "🔷 Rare", 3700),
    ("Silver Wolf", "Honkai: Star Rail", "🔷 Rare", 3500),
    ("March 7th", "Honkai: Star Rail", "⚪ Common", 950),
    ("Welt Yang", "Honkai: Star Rail", "⚪ Common", 850),
    ("Himeko", "Honkai: Star Rail", "⚪ Common", 800),
    ("Herta", "Honkai: Star Rail", "⚪ Common", 750),
    ("Sushang", "Honkai: Star Rail", "⚪ Common", 700),
    ("Tingyun", "Honkai: Star Rail", "⚪ Common", 650),
    ("Fu Xuan", "Honkai: Star Rail", "🟣 Epic", 6000),
    ("Bailu", "Honkai: Star Rail", "🔷 Rare", 2000),
    ("Lynx", "Honkai: Star Rail", "⚪ Common", 500),
]

async def seed_characters():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🎮 Seeding official Genshin Impact & Honkai: Star Rail character entries...")
    async with aiohttp.ClientSession() as session:
        for char_name, series, rarity, favs in TARGET_CHARACTERS:
            try:
                variables = {"name": char_name}
                async with session.post(ANILIST_URL, json={"query": CHAR_SEARCH_QUERY, "variables": variables}, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        char = data.get("data", {}).get("Character")
                        if char:
                            c_id = char["id"]
                            c_full_name = char["name"]["full"]
                            img_url = char["image"]["large"]
                            c_favs = char.get("favourites", favs) or favs

                            cursor.execute("""
                            INSERT OR REPLACE INTO cards_pool (anilist_id, character_name, series_name, image_url, favourites, rarity)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """, (c_id, c_full_name, series, img_url, c_favs, rarity))
                            print(f"  [+] Added: {c_full_name} ({series}) -> {rarity}")
                    await asyncio.sleep(0.15)
            except Exception as e:
                print(f"Error fetching {char_name}: {e}")

    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM cards_pool WHERE series_name IN ('Genshin Impact', 'Honkai: Star Rail')")
    count = cursor.fetchone()[0]
    conn.close()
    print(f"✅ Seeding Complete! Total clean Genshin Impact & Honkai: Star Rail cards: {count}")

if __name__ == "__main__":
    asyncio.run(seed_characters())
