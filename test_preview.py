import asyncio, sys, io, os
sys.path.insert(0, "/Users/user/Desktop/coo-coo-bot")
from PIL import Image
from utils.renderer import render_cards_image, render_single_card
import utils.renderer as renderer

async def _mock_fetch(s, u):
    if "furina" in u or "mythic" in u:
        p = "/Users/user/Desktop/coo-coo-bot/furina_portrait_card.png"
    elif "acheron" in u or "legend" in u:
        p = "/Users/user/Desktop/coo-coo-bot/acheron_portrait_card.png"
    elif "aventurine" in u or "epic" in u:
        p = "/Users/user/Desktop/coo-coo-bot/aventurine_portrait_card.png"
    else:
        p = "/Users/user/Desktop/coo-coo-bot/firefly_cover_card.png"
    
    if os.path.exists(p):
        return Image.open(p).convert("RGBA")
    
    # Create colorful dummy image
    img = Image.new("RGBA", (300, 450), (120, 140, 220, 255))
    return img

renderer.fetch_image = _mock_fetch

async def main():
    cards = [
        {"name": "Citlali", "series": "Genshin Impact", "rarity": "Mythic",
         "image": "furina", "temp_mint": 912, "edition": 2, "code": "vl9bsj3", "quality": "Mint ⭐⭐⭐⭐"},
        {"name": "Acheron", "series": "Honkai: Star Rail", "rarity": "Legendary",
         "image": "acheron", "temp_mint": 3, "edition": 1, "code": "lg3ndy", "quality": "Excellent ⭐⭐⭐"},
        {"name": "Aventurine", "series": "Honkai: Star Rail", "rarity": "Epic",
         "image": "aventurine", "temp_mint": 12, "edition": 1, "code": "ep1c00", "quality": "Good ⭐⭐"},
    ]
    buf = await render_cards_image(cards, show_quality=True)
    with open("/Users/user/Desktop/coo-coo-bot/preview_drop.png", "wb") as f:
        f.write(buf.read())

    single = {
        "character_name": "Citlali", "series_name": "Genshin Impact", "rarity": "Mythic",
        "image_url": "furina", "mint_number": 912, "edition": 2,
        "code": "vl9bsj3", "quality": "Mint ⭐⭐⭐⭐"
    }
    buf2 = await render_single_card(single)
    with open("/Users/user/Desktop/coo-coo-bot/preview_single.png", "wb") as f:
        f.write(buf2.read())
    print("Done! Generated preview_drop.png and preview_single.png")

asyncio.run(main())
