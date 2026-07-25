import asyncio, sys, io, os
sys.path.insert(0, "/Users/user/Desktop/coo-coo-bot")
from PIL import Image, ImageDraw, ImageFont
from utils.renderer import render_cards_image, render_single_card, render_full_art_card
import utils.renderer as renderer

async def _mock_fetch(s, u):
    if "furina" in u or "mythic" in u:
        p = "/Users/user/Desktop/coo-coo-bot/furina_portrait_card.png"
        if os.path.exists(p):
            img = Image.open(p).convert("RGBA")
            return img.crop((35, 10, img.width - 35, 360))
    
    img = Image.new("RGBA", (400, 600), (45, 55, 75, 255))
    d = ImageDraw.Draw(img)
    if "acheron" in u:
        for y in range(600):
            d.line([(0, y), (400, y)], fill=(int(60 - y*0.05), int(40 - y*0.03), int(90 - y*0.08)))
        d.ellipse([100, 150, 300, 380], fill=(220, 200, 240))
        d.ellipse([140, 220, 180, 260], fill=(60, 20, 90))
        d.ellipse([220, 220, 260, 260], fill=(60, 20, 90))
    else:
        for y in range(600):
            d.line([(0, y), (400, y)], fill=(int(90 - y*0.08), int(70 - y*0.06), int(40 - y*0.03)))
        d.ellipse([100, 150, 300, 380], fill=(240, 220, 180))
        d.ellipse([140, 220, 180, 260], fill=(120, 80, 20))
        d.ellipse([220, 220, 260, 260], fill=(120, 80, 20))
        
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
    buf = await render_cards_image(cards, show_quality=False)
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

    buf3 = await render_full_art_card(single)
    with open("/Users/user/Desktop/coo-coo-bot/preview_full_art.png", "wb") as f:
        f.write(buf3.read())
    print("Done! Generated preview_drop.png, preview_single.png, and preview_full_art.png")

asyncio.run(main())
