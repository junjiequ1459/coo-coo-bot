import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_OWNER_IDS = [154017382560563200]

DROP_COOLDOWN_SEC = 900  # 15 Minutes (Standard)
GRAB_COOLDOWN_SEC = 300  # 5 Minutes (Standard)
DROP_PRIORITY_SEC = 10   # 10 Seconds Exclusive Priority Window for the Dropper
DROP_CLAIM_TIMEOUT_SEC = 60  # 60 Seconds Claim Window before cards expire
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
    {"name": "Ratan", "color_desc": "Yellow", "hex": 0xFFFACD},
    {"name": "Miin", "color_desc": "Pink", "hex": 0xFFB6C1},
    {"name": "Coo Coo", "color_desc": "Light Blue", "hex": 0x87CEEB},
]

LEGACY_COLOR_ROLES = [
    "Cherry Pink", "Lavender", "Sunset Red", "Mint Green", "Sky Blue",
    "Lemon Yellow", "Peach Coral", "Royal Blue", "Pure White", "Midnight"
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
