import os
import sqlite3
import shutil
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
BOT_OWNER_IDS = [154017382560563200]

DATA_DIR = os.getenv("DATA_DIR", "/data")
if os.path.exists(DATA_DIR):
    DB_PATH = os.path.join(DATA_DIR, "inventory.db")
    repo_db = os.path.join(os.path.dirname(__file__), "inventory.db")
    
    if not os.path.exists(DB_PATH) and os.path.exists(repo_db):
        try:
            shutil.copyfile(repo_db, DB_PATH)
            print("📦 Successfully seeded Railway /data volume with 10,004 character master database!")
        except Exception as e:
            print(f"Volume seed warning: {e}")

    if os.path.exists(DB_PATH) and os.path.exists(repo_db):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cards_pool'")
            has_table = cur.fetchone()
            if not has_table:
                print("📦 Seeding cards_pool table into Railway volume DB...")
                cur.execute(f"ATTACH DATABASE '{repo_db}' AS repo_db")
                cur.execute("CREATE TABLE cards_pool AS SELECT * FROM repo_db.cards_pool")
                cur.execute("DETACH DATABASE repo_db")
                conn.commit()
                print("📦 Successfully seeded 10,004 cards into Railway volume!")
            conn.close()
        except Exception as e:
            print(f"Volume cards_pool seed warning: {e}")
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

DROP_COOLDOWN_SEC = 900  # 15 Minutes (Standard)
GRAB_COOLDOWN_SEC = 300  # 5 Minutes (Standard)
DAILY_COOLDOWN_SEC = 86400  # 24 Hours

RARITY_WEIGHTS = [
    ("⚪ Common", 0.76),     # 76% Drop Rate
    ("🔷 Rare", 0.15),       # 15% Drop Rate
    ("🟣 Epic", 0.08),       #  8% Drop Rate
    ("✨ Legendary", 0.01)   #  1% Drop Rate
]

RARITY_COLORS = {
    "✨ Legendary": (255, 215, 0),   # Gold
    "🟣 Epic": (147, 112, 219),     # Rich Purple
    "🔷 Rare": (0, 229, 255),       # Cyan Blue
    "⚪ Common": (140, 155, 170)    # Slate Silver
}

BURN_REWARDS = {
    "✨ Legendary": {"dust": 200},
    "🟣 Epic": {"dust": 100},
    "🔷 Rare": {"dust": 50},
    "⚪ Common": {"dust": 20}
}

COLOR_ROLES = [
    {"name": "Cherry Pink", "emoji": "🩷", "hex": 0xFFB6C1},
    {"name": "Lavender", "emoji": "💜", "hex": 0x9370DB},
    {"name": "Sunset Red", "emoji": "🔴", "hex": 0xE60023},
    {"name": "Mint Green", "emoji": "💚", "hex": 0x98FF98},
    {"name": "Sky Blue", "emoji": "🩵", "hex": 0x87CEEB},
    {"name": "Lemon Yellow", "emoji": "💛", "hex": 0xFFFACD},
    {"name": "Peach Coral", "emoji": "🧡", "hex": 0xFF7F50},
    {"name": "Royal Blue", "emoji": "💙", "hex": 0x007AFF},
    {"name": "Pure White", "emoji": "🤍", "hex": 0xFFFFFF},
    {"name": "Midnight", "emoji": "🖤", "hex": 0x36393F},
]

PIGEON_MESSAGES = [
    "Coo coo! 🍞 Don't let a bad sketch ruin your day. Even a dropped bagel on 5th Ave gets a second chance!",
    "Coo coo! 🎨 You don't need perfection, you just need to start. Look at me — I can't read the room, but I still show up!",
    "Coo coo! 🍟 If someone tells you your goals are too big, tell them you're just aerodynamically blessed like me!",
    "Coo coo! 🗽 Life is tough, but so is NYC sidewalk pizza. Keep chewing and keep creating!",
    "Coo coo! 🌾 Take a break, stretch your wrist, and drink water. You can't draw masterpieces on an empty stomach!",
    "Coo coo! 👔 Wear your bowtie with confidence, even when you're just hunting for breadcrumbs!",
    "Coo coo! ✨ Art block is temporary, but your talent is forever. Go make something cool!",
    "Coo coo! 🥯 They said I couldn't fly over the park bench because I was too fat. I waddled instead. Adapt and conquer!",
    "Coo coo! 💅 Never be afraid to third-wheel your own success!",
    "Coo coo! 🎨 Yuki told me every artist starts with a rough draft. Mine was a pretzel stain on the sidewalk!",
    "Coo coo! 🌟 Ratan told me to reach for the stars. I reached for a French fry instead, but the energy is the same!",
    "Coo coo! 🍕 Keep pushing forward! Every line you draw brings you closer to your dream!"
]
