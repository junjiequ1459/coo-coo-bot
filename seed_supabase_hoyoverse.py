import os
import time
import json
import psycopg2
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Load env variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ANILIST_URL = "https://graphql.anilist.co"

# GraphQL Query for Character Search
CHAR_SEARCH_QUERY = """
query ($search: String) {
  Page(page: 1, perPage: 10) {
    characters(search: $search) {
      id
      name {
        full
        alternative
      }
      image {
        large
      }
      favourites
      media(perPage: 5) {
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

# Override dictionary for characters that are either not on AniList,
# or match incorrectly.
CHARACTER_OVERRIDES = {
    # Genshin Impact Overrides
    "Sigewinne": {
        "id": 9900010,
        "name": "Sigewinne",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/0/09/Sigewinne_Wish.png",
        "favourites": 1500
    },
    "Emilie": {
        "id": 9900012,
        "name": "Emilie",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/a/ab/Emilie_Wish.png",
        "favourites": 2100
    },
    "Sethos": {
        "id": 9900011,
        "name": "Sethos",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/f/f6/Sethos_Wish.png",
        "favourites": 600
    },
    "Xianyun": {
        "id": 9900015,
        "name": "Xianyun",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/c/c6/Xianyun_Wish.png",
        "favourites": 3000
    },
    "Gaming": {
        "id": 9900013,
        "name": "Gaming",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/9/98/Gaming_Wish.png",
        "favourites": 1900
    },
    "Chevreuse": {
        "id": 9900016,
        "name": "Chevreuse",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/2/2f/Chevreuse_Wish.png",
        "favourites": 900
    },
    "Chiori": {
        "id": 9900005,
        "name": "Chiori",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/9/9e/Chiori_Wish.png",
        "favourites": 3500
    },
    "Charlotte": {
        "id": 9900006,
        "name": "Charlotte",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/5/5b/Charlotte_Wish.png",
        "favourites": 1200
    },
    "Freminet": {
        "id": 9900008,
        "name": "Freminet",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/1/1b/Freminet_Wish.png",
        "favourites": 800
    },
    "Lyney": {
        "id": 9900009,
        "name": "Lyney",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/f/f9/Lyney_Wish.png",
        "favourites": 4000
    },
    "Lynette": {
        "id": 9900007,
        "name": "Lynette",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/e/e0/Lynette_Wish.png",
        "favourites": 1800
    },
    "Kachina": {
        "id": 9900014,
        "name": "Kachina",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/5/5c/Kachina_Wish.png",
        "favourites": 700
    },
    "Raiden Shogun": {
        "id": 9900021,
        "name": "Raiden Shogun",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/a/a0/Raiden_Shogun_Wish.png",
        "favourites": 15000
    },
    "Nahida": {
        "id": 9900022,
        "name": "Nahida",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/0/05/Nahida_Wish.png",
        "favourites": 9200
    },
    "Kaedehara Kazuha": {
        "id": 9900023,
        "name": "Kaedehara Kazuha",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/1/1e/Kaedehara_Kazuha_Wish.png",
        "favourites": 12500
    },
    "Kamisato Ayaka": {
        "id": 9900024,
        "name": "Kamisato Ayaka",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/a/a0/Kamisato_Ayaka_Wish.png",
        "favourites": 8200
    },
    "Wanderer": {
        "id": 9900025,
        "name": "Wanderer",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/d/d7/Wanderer_Wish.png",
        "favourites": 6500
    },
    "Alhaitham": {
        "id": 9900026,
        "name": "Alhaitham",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/9/90/Alhaitham_Wish.png",
        "favourites": 6000
    },
    "Arataki Itto": {
        "id": 9900027,
        "name": "Arataki Itto",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/b/b4/Arataki_Itto_Wish.png",
        "favourites": 6200
    },
    "Wriothesley": {
        "id": 9900028,
        "name": "Wriothesley",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/e/e2/Wriothesley_Wish.png",
        "favourites": 6000
    },
    "Clorinde": {
        "id": 9900029,
        "name": "Clorinde",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/f/f5/Clorinde_Wish.png",
        "favourites": 6800
    },
    "Yae Miko": {
        "id": 9900030,
        "name": "Yae Miko",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/2/27/Yae_Miko_Wish.png",
        "favourites": 9500
    },
    "Yelan": {
        "id": 9900019,
        "name": "Yelan",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/d/d8/Yelan_Wish.png",
        "favourites": 7500
    },
    "Navia": {
        "id": 9900020,
        "name": "Navia",
        "image": "https://static.wikia.nocookie.net/gensin-impact/images/8/87/Navia_Wish.png",
        "favourites": 7200
    },

    # Honkai: Star Rail Overrides
    "Cyrene": {
        "id": 9900001,
        "name": "Cyrene",
        "image": "https://static.wikia.nocookie.net/houkai-star-rail/images/8/8b/Character_Cyrene_Splash_Art.png",
        "favourites": 3000
    },
    "Jade": {
        "id": 9900004,
        "name": "Jade",
        "image": "https://static.wikia.nocookie.net/houkai-star-rail/images/6/6d/Character_Jade_Splash_Art.png",
        "favourites": 2000
    },
    "Lingsha": {
        "id": 9900002,
        "name": "Lingsha",
        "image": "https://static.wikia.nocookie.net/houkai-star-rail/images/c/c1/Character_Lingsha_Splash_Art.png",
        "favourites": 2500
    },
    "Fugue": {
        "id": 9900003,
        "name": "Tingyun • Fugue",
        "image": "https://static.wikia.nocookie.net/houkai-star-rail/images/4/4c/Character_Fugue_Splash_Art.png",
        "favourites": 2800
    },
    "Topaz": {
        "id": 9900017,
        "name": "Topaz & Numby",
        "image": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/9d/Character_Topaz_and_Numby_Splash_Art.png",
        "favourites": 2200
    },
    "Topaz & Numby": {
        "id": 9900017,
        "name": "Topaz & Numby",
        "image": "https://static.wikia.nocookie.net/houkai-star-rail/images/9/9d/Character_Topaz_and_Numby_Splash_Art.png",
        "favourites": 2200
    },
    "Blade": {
        "id": 9900031,
        "name": "Blade",
        "image": "https://static.wikia.nocookie.net/houkai-star-rail/images/1/16/Character_Blade_Splash_Art.png",
        "favourites": 9000
    },
    "Lynx": {
        "id": 9900018,
        "name": "Lynx",
        "image": "https://static.wikia.nocookie.net/houkai-star-rail/images/3/3c/Character_Lynx_Splash_Art.png",
        "favourites": 500
    }
}

TARGET_CHARACTERS = [
    # --- Genshin Impact ---
    # Legendary (5-stars)
    ("Raiden Shogun", "Genshin Impact", "✨ Legendary", 15000),
    ("Zhongli", "Genshin Impact", "✨ Legendary", 14500),
    ("Hu Tao", "Genshin Impact", "✨ Legendary", 14000),
    ("Furina", "Genshin Impact", "✨ Legendary", 13500),
    ("Neuvillette", "Genshin Impact", "✨ Legendary", 13000),
    ("Arlecchino", "Genshin Impact", "✨ Legendary", 12800),
    ("Kaedehara Kazuha", "Genshin Impact", "✨ Legendary", 12500),
    ("Mualani", "Genshin Impact", "✨ Legendary", 11000),
    ("Kinich", "Genshin Impact", "✨ Legendary", 10500),
    ("Xilonen", "Genshin Impact", "✨ Legendary", 12000),
    ("Chasca", "Genshin Impact", "✨ Legendary", 11500),
    ("Citlali", "Genshin Impact", "✨ Legendary", 10800),
    ("Mavuika", "Genshin Impact", "✨ Legendary", 14800),
    ("Sigewinne", "Genshin Impact", "✨ Legendary", 8500),
    ("Emilie", "Genshin Impact", "✨ Legendary", 8200),
    ("Xianyun", "Genshin Impact", "✨ Legendary", 11200),
    ("Chiori", "Genshin Impact", "✨ Legendary", 9800),
    ("Lyney", "Genshin Impact", "✨ Legendary", 9500),
    
    # Epic
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
    ("Eula", "Genshin Impact", "🟣 Epic", 7000),
    ("Klee", "Genshin Impact", "🟣 Epic", 6500),
    ("Arataki Itto", "Genshin Impact", "🟣 Epic", 6200),
    ("Wriothesley", "Genshin Impact", "🟣 Epic", 6000),
    ("Ororon", "Genshin Impact", "🟣 Epic", 5500),
    ("Iansan", "Genshin Impact", "🟣 Epic", 5200),
    ("Gaming", "Genshin Impact", "🟣 Epic", 5800),
    
    # Rare
    ("Keqing", "Genshin Impact", "🔷 Rare", 3800),
    ("Mona Megistus", "Genshin Impact", "🔷 Rare", 3500),
    ("Fischl", "Genshin Impact", "🔷 Rare", 3200),
    ("Bennett", "Genshin Impact", "🔷 Rare", 3000),
    ("Xiangling", "Genshin Impact", "🔷 Rare", 2800),
    ("Xingqiu", "Genshin Impact", "🔷 Rare", 2600),
    ("Sethos", "Genshin Impact", "🔷 Rare", 2400),
    ("Chevreuse", "Genshin Impact", "🔷 Rare", 2200),
    ("Charlotte", "Genshin Impact", "🔷 Rare", 2100),
    ("Freminet", "Genshin Impact", "🔷 Rare", 2000),
    ("Lynette", "Genshin Impact", "🔷 Rare", 2300),
    ("Kachina", "Genshin Impact", "🔷 Rare", 2200),
    
    # Common
    ("Paimon", "Genshin Impact", "⚪ Common", 900),
    ("Amber", "Genshin Impact", "⚪ Common", 800),
    ("Kaeya Alberich", "Genshin Impact", "⚪ Common", 750),
    ("Lisa Minci", "Genshin Impact", "⚪ Common", 700),

    # --- Honkai: Star Rail (Complete Prydwen Roster) ---
    # Legendary (5-stars & Form Variations)
    ("Acheron", "Honkai: Star Rail", "✨ Legendary", 14000),
    ("Aglaea", "Honkai: Star Rail", "✨ Legendary", 11800),
    ("Anaxa", "Honkai: Star Rail", "✨ Legendary", 10500),
    ("Archer", "Honkai: Star Rail", "✨ Legendary", 11000),
    ("Argenti", "Honkai: Star Rail", "✨ Legendary", 10000),
    ("Ashveil", "Honkai: Star Rail", "✨ Legendary", 10500),
    ("Aventurine", "Honkai: Star Rail", "✨ Legendary", 12800),
    ("Aventurine Waveflair", "Honkai: Star Rail", "✨ Legendary", 13000),
    ("Black Swan", "Honkai: Star Rail", "✨ Legendary", 12500),
    ("Blade", "Honkai: Star Rail", "✨ Legendary", 12000),
    ("Boothill", "Honkai: Star Rail", "✨ Legendary", 11500),
    ("Castorice", "Honkai: Star Rail", "✨ Legendary", 11400),
    ("Cerydra", "Honkai: Star Rail", "✨ Legendary", 10800),
    ("Cipher", "Honkai: Star Rail", "✨ Legendary", 10700),
    ("Clara", "Honkai: Star Rail", "✨ Legendary", 10000),
    ("Cyrene", "Honkai: Star Rail", "✨ Legendary", 13500),
    ("Dan Heng • Imbibitor Lunae", "Honkai: Star Rail", "✨ Legendary", 13800),
    ("Dan Heng • Permansor Terrae", "Honkai: Star Rail", "✨ Legendary", 13500),
    ("Dr. Ratio", "Honkai: Star Rail", "✨ Legendary", 11000),
    ("Evanescia", "Honkai: Star Rail", "✨ Legendary", 10800),
    ("Feixiao", "Honkai: Star Rail", "✨ Legendary", 12200),
    ("Firefly", "Honkai: Star Rail", "✨ Legendary", 13800),
    ("Fu Xuan", "Honkai: Star Rail", "✨ Legendary", 11000),
    ("Gepard", "Honkai: Star Rail", "✨ Legendary", 10000),
    ("Gilgamesh", "Honkai: Star Rail", "✨ Legendary", 14000),
    ("Himeko Nova", "Honkai: Star Rail", "✨ Legendary", 12500),
    ("Huohuo", "Honkai: Star Rail", "✨ Legendary", 11500),
    ("Hyacine", "Honkai: Star Rail", "✨ Legendary", 10600),
    ("Hysilens", "Honkai: Star Rail", "✨ Legendary", 10800),
    ("Jade", "Honkai: Star Rail", "✨ Legendary", 11200),
    ("Jiaoqiu", "Honkai: Star Rail", "✨ Legendary", 10800),
    ("Jing Yuan", "Honkai: Star Rail", "✨ Legendary", 12000),
    ("Jingliu", "Honkai: Star Rail", "✨ Legendary", 12500),
    ("Kafka", "Honkai: Star Rail", "✨ Legendary", 13500),
    ("Lingsha", "Honkai: Star Rail", "✨ Legendary", 11500),
    ("Luocha", "Honkai: Star Rail", "✨ Legendary", 11000),
    ("March 7th • Evernight", "Honkai: Star Rail", "✨ Legendary", 12000),
    ("Mortenax Blade", "Honkai: Star Rail", "✨ Legendary", 11800),
    ("Mydei", "Honkai: Star Rail", "✨ Legendary", 11100),
    ("Phainon", "Honkai: Star Rail", "✨ Legendary", 11200),
    ("Rappa", "Honkai: Star Rail", "✨ Legendary", 10200),
    ("Rin Tohsaka", "Honkai: Star Rail", "✨ Legendary", 13000),
    ("Robin", "Honkai: Star Rail", "✨ Legendary", 12000),
    ("Robin Summeretto", "Honkai: Star Rail", "✨ Legendary", 12200),
    ("Ruan Mei", "Honkai: Star Rail", "✨ Legendary", 12800),
    ("Saber", "Honkai: Star Rail", "✨ Legendary", 14500),
    ("Silver Wolf • Lv. 999", "Honkai: Star Rail", "✨ Legendary", 12500),
    ("Sparkle", "Honkai: Star Rail", "✨ Legendary", 12500),
    ("Sparxie", "Honkai: Star Rail", "✨ Legendary", 11500),
    ("Sunday", "Honkai: Star Rail", "✨ Legendary", 13200),
    ("The Dahlia", "Honkai: Star Rail", "✨ Legendary", 11000),
    ("The Herta", "Honkai: Star Rail", "✨ Legendary", 13000),
    ("Tingyun • Fugue", "Honkai: Star Rail", "✨ Legendary", 12000),
    ("Topaz & Numby", "Honkai: Star Rail", "✨ Legendary", 11500),
    ("Trailblazer • Elation", "Honkai: Star Rail", "✨ Legendary", 11000),
    ("Trailblazer • Remembrance", "Honkai: Star Rail", "✨ Legendary", 11200),
    ("Tribbie", "Honkai: Star Rail", "✨ Legendary", 10900),
    ("Yanqing", "Honkai: Star Rail", "✨ Legendary", 10000),
    ("Yao Guang", "Honkai: Star Rail", "✨ Legendary", 10800),
    ("Yunli", "Honkai: Star Rail", "✨ Legendary", 10500),

    # Epic (4-stars & Special Forms)
    ("Dan Heng", "Honkai: Star Rail", "🟣 Epic", 8800),
    ("Gallagher", "Honkai: Star Rail", "🟣 Epic", 7800),
    ("Guinaifen", "Honkai: Star Rail", "🟣 Epic", 7500),
    ("Hanya", "Honkai: Star Rail", "🟣 Epic", 7200),
    ("Luka", "Honkai: Star Rail", "🟣 Epic", 6800),
    ("March 7th • The Hunt", "Honkai: Star Rail", "🟣 Epic", 8500),
    ("Moze", "Honkai: Star Rail", "🟣 Epic", 7800),
    ("Qingque", "Honkai: Star Rail", "🟣 Epic", 8000),
    ("Sampo", "Honkai: Star Rail", "🟣 Epic", 7200),
    ("Trailblazer • Harmony", "Honkai: Star Rail", "🟣 Epic", 8800),
    ("Trailblazer • Preservation", "Honkai: Star Rail", "🟣 Epic", 8500),
    ("Xueyi", "Honkai: Star Rail", "🟣 Epic", 7000),

    # Rare
    ("Bailu", "Honkai: Star Rail", "🔷 Rare", 3900),
    ("Bronya Rand", "Honkai: Star Rail", "🔷 Rare", 3900),
    ("Pela", "Honkai: Star Rail", "🔷 Rare", 3800),
    ("Seele", "Honkai: Star Rail", "🔷 Rare", 3700),
    ("Serval", "Honkai: Star Rail", "🔷 Rare", 3600),
    ("Silver Wolf", "Honkai: Star Rail", "🔷 Rare", 3500),

    # Common
    ("Arlan", "Honkai: Star Rail", "⚪ Common", 600),
    ("Asta", "Honkai: Star Rail", "⚪ Common", 900),
    ("Herta", "Honkai: Star Rail", "⚪ Common", 950),
    ("Himeko", "Honkai: Star Rail", "⚪ Common", 800),
    ("Hook", "Honkai: Star Rail", "⚪ Common", 650),
    ("Lynx", "Honkai: Star Rail", "⚪ Common", 850),
    ("March 7th", "Honkai: Star Rail", "⚪ Common", 950),
    ("Misha", "Honkai: Star Rail", "⚪ Common", 700),
    ("Natasha", "Honkai: Star Rail", "⚪ Common", 750),
    ("Sushang", "Honkai: Star Rail", "⚪ Common", 700),
    ("Tingyun", "Honkai: Star Rail", "⚪ Common", 850),
    ("Trailblazer • Destruction", "Honkai: Star Rail", "⚪ Common", 900),
    ("Welt", "Honkai: Star Rail", "⚪ Common", 850),
    ("Yukong", "Honkai: Star Rail", "⚪ Common", 650)
]

def seed_database():
    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable is missing!")
        return

    print("🔌 Connecting to Supabase PostgreSQL database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Ensure cards_pool table exists
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
    conn.commit()

    # Clean up known misclassified characters from previous runs
    cursor.execute("""
    DELETE FROM cards_pool 
    WHERE anilist_id IN (126824, 335476, 13580, 14771)
    """)
    conn.commit()
    print("🧹 Cleaned up misclassified characters from cards pool.")

    print(f"🎮 Seeding {len(TARGET_CHARACTERS)} Hoyoverse characters...")
    
    for char_name, series, rarity, default_favs in TARGET_CHARACTERS:
        # Check overrides first
        if char_name in CHARACTER_OVERRIDES:
            ov = CHARACTER_OVERRIDES[char_name]
            c_id = ov["id"]
            c_full_name = ov["name"]
            img_url = ov["image"]
            c_favs = ov["favourites"]
            print(f"  [Override] {char_name} -> {c_full_name} (ID: {c_id})")
        else:
            # Query AniList
            retries = 3
            success = False
            c_id = None
            c_full_name = char_name
            img_url = None
            c_favs = default_favs

            while retries > 0 and not success:
                req = urllib.request.Request(
                    ANILIST_URL,
                    data=json.dumps({'query': CHAR_SEARCH_QUERY, 'variables': {'search': char_name}}).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
                )
                try:
                    with urllib.request.urlopen(req) as response:
                        data = json.loads(response.read().decode('utf-8'))
                        chars = data.get('data', {}).get('Page', {}).get('characters', [])
                        
                        match = None
                        # Filter by media
                        for c in chars:
                            media_nodes = c.get('media', {}).get('nodes', [])
                            is_hoyoverse = False
                            for node in media_nodes:
                                titles = node.get('title', {})
                                title_str = ' '.join(filter(None, [titles.get('english'), titles.get('romaji')])).lower()
                                if 'genshin' in title_str or 'honkai' in title_str or 'star rail' in title_str:
                                    is_hoyoverse = True
                                    break
                            if is_hoyoverse:
                                match = c
                                break
                        
                        if not match and chars:
                            # Strict name match fallback
                            for c in chars:
                                if char_name.lower() in c['name']['full'].lower():
                                    match = c
                                    break

                        if match:
                            c_id = match['id']
                            c_full_name = match['name']['full']
                            img_url = match['image']['large']
                            c_favs = match.get('favourites', default_favs) or default_favs
                            print(f"  [AniList] Found {char_name} -> {c_full_name} (ID: {c_id})")
                        else:
                            print(f"  [AniList] Not found {char_name}, using fallbacks")
                        success = True
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        print(f"  [429] Rate limited. Sleeping 5s before retrying {char_name}...")
                        time.sleep(5)
                        retries -= 1
                    else:
                        print(f"  [HTTP ERROR] {char_name}: {e.code}. Using fallbacks.")
                        success = True
                except Exception as e:
                    print(f"  [ERROR] {char_name}: {e}. Using fallbacks.")
                    success = True

            # If no AniList ID was found, generate a custom one
            if not c_id:
                c_id = 9900000 + abs(hash(char_name)) % 100000
            
            if not img_url:
                # High-res fallback image from Fandom Wikia for any character missing an image
                c_clean = char_name.replace(' • ', '_').replace(' & ', '_and_').replace('.', '').replace(':', '').replace(' ', '_')
                img_url = f"https://static.wikia.nocookie.net/houkai-star-rail/images/8/80/Character_{c_clean}_Splash_Art.png"
                print(f"  [Image fallback] {char_name} -> {img_url}")

            time.sleep(1.0) # rate limit prevention sleep

        # Perform PostgreSQL Upsert
        try:
            cursor.execute("""
            INSERT INTO cards_pool (anilist_id, character_name, series_name, image_url, favourites, rarity)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (anilist_id)
            DO UPDATE SET
                character_name = EXCLUDED.character_name,
                series_name = EXCLUDED.series_name,
                image_url = EXCLUDED.image_url,
                favourites = EXCLUDED.favourites,
                rarity = EXCLUDED.rarity
            """, (c_id, c_full_name, series, img_url, c_favs, rarity))
        except Exception as e:
            print(f"❌ Failed to upsert {c_full_name} to database: {e}")
            conn.rollback()
        else:
            conn.commit()

    # Count database cards
    cursor.execute("SELECT series_name, COUNT(*) FROM cards_pool GROUP BY series_name")
    summary = cursor.fetchall()
    print("\n✅ Seeding Complete! Supabase Database Summary:")
    for series, count in summary:
        print(f"  - {series}: {count} cards")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    seed_database()
