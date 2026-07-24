import io
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from config import RARITY_COLORS

async def fetch_image(session, url):
    try:
        async with session.get(url, timeout=8) as resp:
            if resp.status == 200:
                data = await resp.read()
                return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        print(f"Failed to fetch image {url}: {e}")
    img = Image.new("RGBA", (260, 400), (32, 34, 37, 255))
    return img

def apply_quality_filter_to_image(img: Image.Image, quality_str: str) -> Image.Image:
    """Applies visual quality filters (wear, scratches, fade, desaturation, gold shine) to PIL card artwork!"""
    q_clean = quality_str.lower()

    if "damaged" in q_clean or "❌" in q_clean:
        # Damaged: Heavy red tint, 60% desaturated, dull contrast
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.4)
        enhancer_c = ImageEnhance.Contrast(img)
        img = enhancer_c.enhance(0.8)
        overlay = Image.new("RGBA", img.size, (150, 0, 0, 45))
        img = Image.alpha_composite(img.convert("RGBA"), overlay)
        return img

    elif "poor" in q_clean or (q_clean.startswith("poor") and "⭐⭐" not in q_clean):
        # Poor ⭐: Faded, 40% desaturated vintage worn look with warm sepia grain
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.6)
        enhancer_b = ImageEnhance.Brightness(img)
        img = enhancer_b.enhance(0.88)
        overlay = Image.new("RGBA", img.size, (110, 80, 50, 40))
        img = Image.alpha_composite(img.convert("RGBA"), overlay)
        return img

    elif "good" in q_clean:
        # Good ⭐⭐: Standard clean artwork
        return img

    elif "excellent" in q_clean:
        # Excellent ⭐⭐⭐: Enhanced contrast + vibrant color boost
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.15)
        enhancer_c = ImageEnhance.Contrast(img)
        img = enhancer_c.enhance(1.1)
        return img

    elif "mint" in q_clean:
        # Mint ⭐⭐⭐⭐: Gold/Pristine high contrast + crisp vibrant colors & sharpness
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.25)
        enhancer_c = ImageEnhance.Contrast(img)
        img = enhancer_c.enhance(1.15)
        enhancer_s = ImageEnhance.Sharpness(img)
        img = enhancer_s.enhance(1.3)
        return img

    return img

def apply_quality_effects_on_artwork(draw, x: int, y: int, w: int, h: int, quality_str: str):
    """Renders quality badges and wear/crack/sparkle artwork effects directly on PIL card image canvas!"""
    q_clean = quality_str.lower()
    
    if "damaged" in q_clean or "❌" in q_clean:
        # Draw cracked glass scratch lines across the artwork
        draw.line([x + 10, y + 15, x + w // 2, y + h // 2], fill=(255, 255, 255, 220), width=2)
        draw.line([x + w // 2, y + h // 2, x + w - 15, y + h // 3], fill=(240, 240, 240, 220), width=2)
        draw.line([x + w // 2, y + h // 2, x + w // 3, y + h - 20], fill=(230, 230, 230, 220), width=2)
        draw.line([x + w // 3, y + h - 20, x + 25, y + h - 40], fill=(200, 200, 200, 180), width=1)
        
        # Red Damaged badge on artwork top-right
        badge_w, badge_h = 95, 22
        bx1 = x + w - badge_w - 6
        by1 = y + 6
        bx2 = x + w - 6
        by2 = y + 6 + badge_h
        draw.rectangle([bx1, by1, bx2, by2], fill=(180, 20, 20, 240), outline=(255, 60, 60), width=1)
        draw.text((bx1 + 6, by1 + 3), "🔴 DAMAGED ❌", fill=(255, 255, 255))
    
    elif "poor" in q_clean or (q_clean.startswith("poor") and "⭐⭐" not in q_clean):
        # Draw scuffed wear scratches & worn corner marks on Poor card
        draw.line([x + 6, y + 8, x + 35, y + 22], fill=(180, 150, 110, 200), width=1)
        draw.line([x + w - 30, y + h - 15, x + w - 8, y + h - 28], fill=(180, 150, 110, 200), width=1)
        draw.line([x + 12, y + h - 35, x + 40, y + h - 12], fill=(160, 130, 90, 180), width=1)
        
        # Worn scuffed border outline inside portrait
        draw.rectangle([x + 2, y + 2, x + w - 2, y + h - 2], outline=(140, 100, 60, 180), width=1)

        badge_w, badge_h = 75, 22
        bx1 = x + w - badge_w - 6
        by1 = y + 6
        bx2 = x + w - 6
        by2 = y + 6 + badge_h
        draw.rectangle([bx1, by1, bx2, by2], fill=(40, 25, 15, 240), outline=(255, 140, 0), width=1)
        draw.text((bx1 + 6, by1 + 3), "🟠 Poor ⭐", fill=(255, 165, 0))

    elif "mint" in q_clean or "⭐⭐⭐⭐" in q_clean:
        # Gold sparkles on Mint card
        draw.text((x + 8, y + 8), "✨", fill=(255, 215, 0))
        draw.text((x + w - 22, y + h - 26), "✨", fill=(255, 215, 0))

        badge_w, badge_h = 100, 22
        bx1 = x + w - badge_w - 6
        by1 = y + 6
        bx2 = x + w - 6
        by2 = y + 6 + badge_h
        draw.rectangle([bx1, by1, bx2, by2], fill=(20, 25, 30, 240), outline=(255, 215, 0), width=1)
        draw.text((bx1 + 6, by1 + 3), "✨ Mint ⭐⭐⭐⭐", fill=(255, 215, 0))

    elif "excellent" in q_clean or "⭐⭐⭐" in q_clean:
        # Violet shimmer sparkles on Excellent card
        draw.text((x + 8, y + 8), "🌟", fill=(200, 160, 255))

        badge_w, badge_h = 105, 22
        bx1 = x + w - badge_w - 6
        by1 = y + 6
        bx2 = x + w - 6
        by2 = y + 6 + badge_h
        draw.rectangle([bx1, by1, bx2, by2], fill=(20, 25, 30, 240), outline=(147, 112, 219), width=1)
        draw.text((bx1 + 6, by1 + 3), "🌟 Excellent ⭐⭐⭐", fill=(200, 160, 255))

    elif "good" in q_clean or "⭐⭐" in q_clean:
        badge_w, badge_h = 80, 22
        bx1 = x + w - badge_w - 6
        by1 = y + 6
        bx2 = x + w - 6
        by2 = y + 6 + badge_h
        draw.rectangle([bx1, by1, bx2, by2], fill=(20, 25, 30, 240), outline=(0, 229, 255), width=1)
        draw.text((bx1 + 6, by1 + 3), "⚪ Good ⭐⭐", fill=(0, 229, 255))

async def render_three_cards_composite(cards: list) -> io.BytesIO:
    """Renders a single horizontal 3-card composite image (850x450 px) matching Karuta's exact frame style!"""
    canvas_w, canvas_h = 850, 450
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(canvas)

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_image(session, card["image"]) for card in cards]
        raw_images = await asyncio.gather(*tasks)

    card_w, card_h = 255, 400
    padding_x = 20
    padding_y = 25

    for idx, card in enumerate(cards):
        x = padding_x + idx * (card_w + 20)
        y = padding_y
        rc = RARITY_COLORS.get(card["rarity"], (140, 155, 170))

        draw.rectangle([x, y, x + card_w, y + card_h], fill=(28, 30, 34, 255), outline=(60, 65, 75), width=2)
        draw.rectangle([x + 4, y + 4, x + card_w - 4, y + card_h - 4], outline=rc, width=2)
        
        raw_img = raw_images[idx]
        img_w, img_h = card_w - 14, card_h - 68
        resized_img = raw_img.resize((img_w, img_h), Image.Resampling.LANCZOS)
        canvas.paste(resized_img, (x + 7, y + 7))

        badge_poly = [(x + 4, y + 4), (x + 38, y + 4), (x + 44, y + 16), (x + 38, y + 34), (x + 4, y + 34)]
        draw.polygon(badge_poly, fill=(15, 16, 18), outline=rc)
        draw.text((x + 16, y + 10), str(idx + 1), fill=(255, 255, 255))
        
        box_y1 = y + card_h - 60
        box_y2 = y + card_h - 6
        draw.rectangle([x + 6, box_y1, x + card_w - 6, box_y2], fill=(12, 13, 15, 245))
        draw.line([x + 10, box_y1 + 8, x + 10, box_y2 - 8], fill=rc, width=3)
        
        draw.text((x + 18, box_y1 + 6), f"ED 1 | #{card['temp_mint']}", fill=(255, 215, 0))
        draw.text((x + 18, box_y1 + 30), f"ID: {card['code']}", fill=(180, 190, 200))

        char_disp = card['name'][:24]
        series_disp = card['series'][:24]
        draw.text((x + card_w - 14, box_y1 + 6), char_disp, fill=(255, 255, 255), anchor="ra")
        draw.text((x + card_w - 14, box_y1 + 30), series_disp, fill=(150, 165, 180), anchor="ra")

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

async def render_single_card(card_data: dict) -> io.BytesIO:
    """Renders a single high-quality framed Karuta card for /card."""
    card_w, card_h = 340, 520
    canvas = Image.new("RGBA", (card_w, card_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(canvas)

    async with aiohttp.ClientSession() as session:
        raw_img = await fetch_image(session, card_data["image_url"])

    rc = RARITY_COLORS.get(card_data["rarity"], (140, 155, 170))
    q_val = card_data.get("quality", "Good ⭐⭐")

    q_clean = q_val.lower()
    if "damaged" in q_clean or "❌" in q_clean:
        border_col = (255, 50, 50)
    elif "poor" in q_clean or (q_clean.startswith("poor") and "⭐⭐" not in q_clean):
        border_col = (220, 130, 40)
    elif "excellent" in q_clean:
        border_col = (180, 120, 255)
    elif "mint" in q_clean:
        border_col = (255, 215, 0)
    else:
        border_col = rc

    draw.rectangle([0, 0, card_w, card_h], fill=(28, 30, 34, 255), outline=(60, 65, 75), width=3)
    draw.rectangle([5, 5, card_w - 5, card_h - 5], outline=border_col, width=3)

    img_w, img_h = card_w - 18, card_h - 80
    resized_img = raw_img.resize((img_w, img_h), Image.Resampling.LANCZOS)
    
    # Apply Visual Quality Filter (Faded wear for Poor, Red tint for Damaged, Gold shine for Mint!)
    filtered_img = apply_quality_filter_to_image(resized_img, q_val)

    canvas.paste(filtered_img, (9, 9))

    # Apply Quality overlay effects, wear scratches & badges on artwork
    apply_quality_effects_on_artwork(draw, 9, 9, img_w, img_h, q_val)

    box_y1 = card_h - 72
    box_y2 = card_h - 8
    draw.rectangle([8, box_y1, card_w - 8, box_y2], fill=(12, 13, 15, 245))
    draw.line([14, box_y1 + 10, 14, box_y2 - 10], fill=border_col, width=4)

    draw.text((24, box_y1 + 10), f"ED {card_data.get('edition', 1)} | #{card_data['mint_number']}", fill=(255, 215, 0))
    draw.text((24, box_y1 + 34), f"ID: {card_data['code'].upper()}", fill=(240, 240, 240))

    char_disp = card_data['character_name'][:26]
    series_disp = card_data['series_name'][:26]
    draw.text((card_w - 18, box_y1 + 10), char_disp, fill=(255, 255, 255), anchor="ra")
    draw.text((card_w - 18, box_y1 + 34), series_disp, fill=(160, 175, 190), anchor="ra")

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf
