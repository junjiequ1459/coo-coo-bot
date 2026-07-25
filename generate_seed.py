import urllib.request
import json
import time

# 1. Genshin Characters
url_g = 'https://genshin-impact.fandom.com/api.php?action=query&list=categorymembers&cmtitle=Category:Playable_Characters&cmlimit=500&format=json'
req_g = urllib.request.Request(url_g, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_g) as response:
    data = json.loads(response.read().decode('utf-8'))
    members = data.get('query', {}).get('categorymembers', [])
    genshin_chars = [m['title'] for m in members if not m['title'].startswith('Category:') and m['title'] not in ['Aether', 'Lumine', 'Manekin', 'Manekina', 'Wonderland Manekin']]

genshin_data = {}
batch_size = 30
for i in range(0, len(genshin_chars), batch_size):
    batch = genshin_chars[i:i+batch_size]
    titles = [f"File:{name.replace(' ', '_')}_Wish.png" for name in batch]
    titles_str = '|'.join(titles)
    
    api_url = f'https://genshin-impact.fandom.com/api.php?action=query&titles={urllib.parse.quote(titles_str)}&prop=imageinfo&iiprop=url&format=json'
    req_api = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req_api) as resp:
            d = json.loads(resp.read().decode('utf-8'))
            pages = d.get('query', {}).get('pages', {})
            for pid, info in pages.items():
                title = info.get('title', '')
                imageinfo = info.get('imageinfo', [])
                if imageinfo:
                    clean_name = title.replace('File:', '').replace(' Wish.png', '').replace('_', ' ').strip()
                    genshin_data[clean_name] = imageinfo[0]['url']
    except Exception as e:
        pass
    time.sleep(0.1)

# 2. Prydwen HSR Characters
hsr_chars = [
    'Acheron', 'Aglaea', 'Anaxa', 'Archer', 'Argenti', 'Arlan', 'Ashveil', 'Asta',
    'Aventurine', 'Aventurine Waveflair', 'Bailu', 'Black Swan', 'Blade', 'Boothill',
    'Bronya', 'Castorice', 'Cerydra', 'Cipher', 'Clara', 'Cyrene', 'Dan Heng',
    'Dan Heng • Imbibitor Lunae', 'Dan Heng • Permansor Terrae', 'Dr. Ratio', 'Evanescia',
    'Feixiao', 'Firefly', 'Fu Xuan', 'Gallagher', 'Gepard', 'Gilgamesh', 'Guinaifen',
    'Hanya', 'Herta', 'Himeko', 'Himeko Nova', 'Hook', 'Huohuo', 'Hyacine', 'Hysilens',
    'Jade', 'Jiaoqiu', 'Jing Yuan', 'Jingliu', 'Kafka', 'Lingsha', 'Luka', 'Luocha',
    'Lynx', 'March 7th', 'March 7th • Evernight', 'March 7th • The Hunt', 'Misha',
    'Mortenax Blade', 'Moze', 'Mydei', 'Natasha', 'Pela', 'Phainon', 'Qingque',
    'Rappa', 'Rin Tohsaka', 'Robin', 'Robin Summeretto', 'Ruan Mei', 'Saber', 'Sampo',
    'Seele', 'Serval', 'Silver Wolf', 'Silver Wolf • Lv. 999', 'Sparkle', 'Sparxie',
    'Sunday', 'Sushang', 'The Dahlia', 'The Herta', 'Tingyun', 'Fugue',
    'Topaz & Numby', 'Trailblazer • Destruction', 'Trailblazer • Elation',
    'Trailblazer • Harmony', 'Trailblazer • Preservation', 'Trailblazer • Remembrance',
    'Tribbie', 'Welt', 'Xueyi', 'Yanqing', 'Yao Guang', 'Yukong', 'Yunli'
]

hsr_data = {}
for i in range(0, len(hsr_chars), batch_size):
    batch = hsr_chars[i:i+batch_size]
    titles = [f"File:Character_{name.replace(' • ', '_').replace(' & ', '_and_').replace('.', '').replace(':', '').replace(' ', '_')}_Splash_Art.png" for name in batch]
    titles_str = '|'.join(titles)
    
    api_url = f'https://honkai-star-rail.fandom.com/api.php?action=query&titles={urllib.parse.quote(titles_str)}&prop=imageinfo&iiprop=url&format=json'
    req_api = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req_api) as resp:
            d = json.loads(resp.read().decode('utf-8'))
            pages = d.get('query', {}).get('pages', {})
            for pid, info in pages.items():
                title = info.get('title', '')
                imageinfo = info.get('imageinfo', [])
                if imageinfo:
                    for name in batch:
                        expected_title = f"File:Character_{name.replace(' • ', '_').replace(' & ', '_and_').replace('.', '').replace(':', '').replace(' ', '_')}_Splash_Art.png".replace('_', ' ')
                        if title.lower() == expected_title.lower():
                            hsr_data[name] = imageinfo[0]['url']
                            break
    except Exception as e:
        pass
    time.sleep(0.1)

template = f"""import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

GENSHIN_CHARACTERS = {json.dumps(genshin_data, indent=4)}

HSR_CHARACTERS = {json.dumps(hsr_data, indent=4)}

HSR_CHAR_NAMES = {json.dumps(hsr_chars, indent=4)}

LOW_RARITY_HINTS = {{'Amber', 'Kaeya', 'Lisa', 'Barbara', 'Razor', 'Xiangling', 'Beidou', 'Xingqiu', 'Ningguang', 'Fischl', 'Bennett', 'Noelle', 'Chongyun', 'Sucrose', 'Diona', 'Xinyan', 'Rosaria', 'Yanfei', 'Sayu', 'Kujou Sara', 'Thoma', 'Gorou', 'Yun Jin', 'Kuki Shinobu', 'Heizou', 'Collei', 'Dori', 'Candace', 'Layla', 'Faruzan', 'Yaoyao', 'Kaveh', 'Kirara', 'Lynette', 'Freminet', 'Charlotte', 'Chevreuse', 'Gaming', 'Sethos', 'Kachina', 'Ororon', 'Iansan', 'Arlan', 'Asta', 'Herta', 'Serval', 'Natasha', 'Pela', 'Sampo', 'Hook', 'Qingque', 'Tingyun', 'Sushang', 'Yukong', 'Luka', 'Lynx', 'Guinaifen', 'Hanya', 'Xueyi', 'Misha', 'Gallagher', 'Moze'}}

def seed_database():
    if not DATABASE_URL:
        print("❌ DATABASE_URL missing!")
        return

    print("🔌 Connecting to Supabase PostgreSQL database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cards_pool (
        id SERIAL PRIMARY KEY,
        anilist_id INTEGER UNIQUE,
        character_name TEXT NOT NULL,
        series_name TEXT NOT NULL,
        image_url TEXT NOT NULL,
        favourites INTEGER DEFAULT 0,
        rarity TEXT NOT NULL
    )
    ''')
    conn.commit()

    # Clean up misclassified characters from previous runs
    cursor.execute("DELETE FROM cards_pool WHERE anilist_id IN (126824, 335476, 13580, 14771, 174356, 263449)")
    conn.commit()

    total_inserted = 0

    # 1. Genshin Characters (116 total)
    print(f"🎮 Seeding {{len(GENSHIN_CHARACTERS)}} Genshin Impact characters...")
    for name, img_url in GENSHIN_CHARACTERS.items():
        anilist_id = 9910000 + abs(hash(name)) % 100000
        rarity = "🔷 Rare" if name in LOW_RARITY_HINTS else "✨ Legendary"
        favs = 3000 if rarity == "🔷 Rare" else 12000

        cursor.execute('''
        INSERT INTO cards_pool (anilist_id, character_name, series_name, image_url, favourites, rarity)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (anilist_id) DO UPDATE SET
            character_name = EXCLUDED.character_name,
            series_name = EXCLUDED.series_name,
            image_url = EXCLUDED.image_url,
            favourites = EXCLUDED.favourites,
            rarity = EXCLUDED.rarity
        ''', (anilist_id, name, "Genshin Impact", img_url, favs, rarity))
        total_inserted += 1

    # 2. Honkai: Star Rail Characters (92 total)
    print(f"🎮 Seeding {{len(HSR_CHAR_NAMES)}} Honkai: Star Rail characters...")
    for name in HSR_CHAR_NAMES:
        img_url = HSR_CHARACTERS.get(name)
        if not img_url:
            c_clean = name.replace(' • ', '_').replace(' & ', '_and_').replace('.', '').replace(':', '').replace(' ', '_')
            img_url = f"https://static.wikia.nocookie.net/houkai-star-rail/images/8/80/Character_{{c_clean}}_Splash_Art.png"

        anilist_id = 9920000 + abs(hash(name)) % 100000
        rarity = "🔷 Rare" if name in LOW_RARITY_HINTS or name in ['March 7th', 'Welt', 'Himeko', 'Arlan', 'Asta', 'Hook', 'Natasha', 'Misha', 'Sushang', 'Yukong'] else "✨ Legendary"
        favs = 3000 if rarity == "🔷 Rare" else 12000

        cursor.execute('''
        INSERT INTO cards_pool (anilist_id, character_name, series_name, image_url, favourites, rarity)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (anilist_id) DO UPDATE SET
            character_name = EXCLUDED.character_name,
            series_name = EXCLUDED.series_name,
            image_url = EXCLUDED.image_url,
            favourites = EXCLUDED.favourites,
            rarity = EXCLUDED.rarity
        ''', (anilist_id, name, "Honkai: Star Rail", img_url, favs, rarity))
        total_inserted += 1

    conn.commit()

    cursor.execute("SELECT series_name, COUNT(*) FROM cards_pool WHERE series_name IN ('Genshin Impact', 'Honkai: Star Rail') GROUP BY series_name")
    summary = cursor.fetchall()
    print("\\n✅ Complete Hoyoverse Seeding Finished! Final Counts in Supabase:")
    for series, count in summary:
        print(f"  - {{series}}: {{count}} cards")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    seed_database()
"""

with open('seed_supabase_hoyoverse.py', 'w') as f:
    f.write(template)

print("Generator finished! seed_supabase_hoyoverse.py has been created.")
