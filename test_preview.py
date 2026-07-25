import asyncio, sys, io, os
sys.path.insert(0, "/Users/user/Desktop/coo-coo-bot")
from PIL import Image, ImageDraw, ImageFont
from utils.renderer import render_cards_image, render_single_card, render_full_art_card
import utils.renderer as renderer

async def _mock_fetch(s, u):
    # Test with unzoomed full character illustration
    p = "/Users/user/Desktop/coo-coo-bot/furina_portrait_card.png"
    if os.path.exists(p):
        img = Image.open(p).convert("RGBA")
        # Extract pure raw character image
        return img.crop((35, 65, img.width - 35, 340))
    
    img = Image.new("RGBA", (400, 600), (45, 55, 75, 255))
    d = ImageDraw.Draw(img)
    return img

renderer.fetch_image = _mock_fetch

async def main():
    cards = [
        {"name": "Citlali", "series": "Genshin Impact", "rarity": "Mythic",
         "image": "citlali", "temp_mint": 912, "edition": 2, "code": "vl9bsj3", "quality": "Mint ⭐⭐⭐⭐"},
        {"name": "Acheron", "series": "Honkai: Star Rail", "rarity": "Legendary",
         "image": "acheron", "temp_mint": 3, "edition": 1, "code": "lg3ndy", "quality": "Excellent ⭐⭐⭐"},
        {"name": "Aventurine", "series": "Honkai: Star Rail", "rarity": "Epic",
         "image": "aventurine", "temp_mint": 12, "edition": 1, "code": "ep1c00", "quality": "Good ⭐⭐"},
    ]
    buf = await render_cards_image(cards, show_quality=False)
    with open("/Users/user/Desktop/coo-coo-bot/preview_drop.png", "wb") as f:
        f.write(buf.read())

    # Single Mythic Card Preview
    single_mythic = {
        "character_name": "Citlali", "series_name": "Genshin Impact", "rarity": "Mythic",
        "image_url": "citlali", "mint_number": 912, "edition": 2,
        "code": "vl9bsj3", "quality": "Mint ⭐⭐⭐⭐"
    }
    buf2 = await render_single_card(single_mythic)
    with open("/Users/user/Desktop/coo-coo-bot/preview_single.png", "wb") as f:
        f.write(buf2.read())

    buf3 = await render_full_art_card(single_mythic)
    with open("/Users/user/Desktop/coo-coo-bot/preview_full_art.png", "wb") as f:
        f.write(buf3.read())
    print("Done!")

asyncio.run(main())
