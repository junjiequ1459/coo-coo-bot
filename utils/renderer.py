import io
import os
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from config import RARITY_COLORS

# ==========================================
# 🔤 FONT LOADING
# ==========================================
def _load_font(size):
    """Try to load a good system font, fall back to default."""
    font_paths = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSRounded.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()

# Pre-load fonts at various sizes for drop cards and single cards
FONT_DROP_TITLE = _load_font(16)      # Character name on drop cards
FONT_DROP_SUBTITLE = _load_font(13)   # Series name / ID on drop cards
FONT_DROP_BADGE = _load_font(14)      # ED 1 | #mint on drop cards
FONT_SINGLE_TITLE = _load_font(20)    # Character name on single card
FONT_SINGLE_SUBTITLE = _load_font(15) # Series name / ID on single card
FONT_SINGLE_BADGE = _load_font(17)    # ED 1 | #mint on single card

# Shared aiohttp session — reused across all renders to avoid SSL handshake overhead
_http_session = None

async def get_http_session():
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=10, keepalive_timeout=60)
        )
    return _http_session

async def fetch_image(session, url):
    try:
        if url and str(url).startswith("http"):
            async with session.get(url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        print(f"Failed to fetch image '{url}': {e}")
    img = Image.new("RGBA", (260, 400), (32, 34, 37, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 250, 390], outline=(70, 75, 85), width=2)
    draw.text((30, 190), "Image Unavailable", fill=(160, 175, 190))
    return img

def apply_quality_filter_to_image(img: Image.Image, quality_str: str) -> Image.Image:
    """Applies visual quality wear filters scaled strictly by tier (ONLY Mint is pure original)!"""
    q_clean = quality_str.lower()

    if "mint" in q_clean or "⭐⭐⭐⭐" in q_clean:
        # Mint ⭐⭐⭐⭐: ONLY Mint is pure 100% original untouched image!
        return img

    elif "excellent" in q_clean or "⭐⭐⭐" in q_clean:
        # Excellent ⭐⭐⭐: Very slightly worn (15% desaturation)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.85)
        return img

    elif "good" in q_clean or "⭐⭐" in q_clean:
        # Good ⭐⭐: Moderately worn (30% desaturation & slight fade)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.70)
        enhancer_b = ImageEnhance.Brightness(img)
        img = enhancer_b.enhance(0.95)
        return img

    elif "poor" in q_clean or (q_clean.startswith("poor") and "⭐⭐" not in q_clean):
        # Poor ⭐: Heavily worn & grainy (65% desaturation + sepia vintage film texture)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.35)
        enhancer_b = ImageEnhance.Brightness(img)
        img = enhancer_b.enhance(0.82)
        enhancer_c = ImageEnhance.Contrast(img)
        img = enhancer_c.enhance(1.20)
        overlay = Image.new("RGBA", img.size, (130, 95, 60, 60))
        img = Image.alpha_composite(img.convert("RGBA"), overlay)
        return img

    elif "damaged" in q_clean or "❌" in q_clean:
        # Damaged: 80% desaturation + physical wear (No artificial red tint!)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.20)
        enhancer_b = ImageEnhance.Brightness(img)
        img = enhancer_b.enhance(0.75)
        return img

    return img

def apply_quality_effects_on_artwork(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, quality_str: str):
    """Draws physical scratches, shattered glass corner cracks, and clean pill text badges on artwork canvas."""
    q_clean = quality_str.lower()

    # --- PHYSICAL EDGE WEAR & SCRATCHES (POOR & DAMAGED CARDS) ---
    if "poor" in q_clean or "damaged" in q_clean or "❌" in q_clean:
        scratch_col = (200, 200, 200, 110)
        draw.line([x + 12, y + 25, x + 65, y + 70], fill=scratch_col, width=1)
        draw.line([x + w - 40, y + h - 90, x + w - 15, y + h - 35], fill=scratch_col, width=1)
        draw.line([x + 30, y + h - 50, x + 90, y + h - 20], fill=scratch_col, width=1)

    # --- ORGANIC SHATTERED GLASS CORNER/EDGE CRACKS (DAMAGED CARDS ONLY - NO FACE CROSSHAIRS) ---
    if "damaged" in q_clean or "❌" in q_clean:
        crack_col = (235, 235, 245, 170)

        # Top-Left Corner Fractures
        tl_x, tl_y = x + 4, y + 4
        draw.line([tl_x, tl_y, tl_x + 35, tl_y + 25], fill=crack_col, width=2)
        draw.line([tl_x + 35, tl_y + 25, tl_x + 55, tl_y + 15], fill=crack_col, width=1)
        draw.line([tl_x + 35, tl_y + 25, tl_x + 42, tl_y + 50], fill=crack_col, width=1)

        # Bottom-Right Corner Fractures
        br_x, br_y = x + w - 4, y + h - 4
        draw.line([br_x, br_y, br_x - 45, br_y - 30], fill=crack_col, width=2)
        draw.line([br_x - 45, br_y - 30, br_x - 70, br_y - 20], fill=crack_col, width=1)
        draw.line([br_x - 45, br_y - 30, br_x - 35, br_y - 60], fill=crack_col, width=1)

        # Right Edge Impact Crack
        re_x, re_y = x + w - 4, y + (h // 2) - 30
        draw.line([re_x, re_y, re_x - 30, re_y + 20], fill=crack_col, width=2)
        draw.line([re_x - 30, re_y + 20, re_x - 55, re_y + 10], fill=crack_col, width=1)
        draw.line([re_x - 30, re_y + 20, re_x - 40, re_y + 45], fill=crack_col, width=1)

    # --- CLEAN TYPOGRAPHY PILL BADGES ---
    badge_label = "Good"
    badge_fill = (0, 180, 215, 230)
    text_color = (255, 255, 255)

    if "mint" in q_clean or "⭐⭐⭐⭐" in q_clean:
        badge_label = "Mint"
        badge_fill = (215, 165, 0, 240)
        text_color = (20, 20, 20)
    elif "excellent" in q_clean or "⭐⭐⭐" in q_clean:
        badge_label = "Excellent"
        badge_fill = (150, 80, 230, 230)
        text_color = (255, 255, 255)
    elif "good" in q_clean or "⭐⭐" in q_clean:
        badge_label = "Good"
        badge_fill = (0, 170, 200, 230)
        text_color = (255, 255, 255)
    elif "poor" in q_clean or (q_clean.startswith("poor") and "⭐⭐" not in q_clean):
        badge_label = "Poor"
        badge_fill = (210, 110, 20, 230)
        text_color = (255, 255, 255)
    elif "damaged" in q_clean or "❌" in q_clean:
        badge_label = "Damaged"
        badge_fill = (90, 95, 105, 230)
        text_color = (255, 255, 255)

    badge_x1, badge_y1 = x + 8, y + 8
    badge_w = 12 + (len(badge_label) * 7)
    badge_h = 18
    draw.rectangle([badge_x1, badge_y1, badge_x1 + badge_w, badge_y1 + badge_h], fill=badge_fill)
    draw.text((badge_x1 + 6, badge_y1 + 2), badge_label, fill=text_color)

async def render_cards_image(cards: list, show_quality: bool = False) -> io.BytesIO:
    """Renders 3 cards side-by-side on a single image canvas for /drop."""
    card_w, card_h = 260, 400
    gap = 20
    canvas_w = (card_w * 3) + (gap * 2) + 40
    canvas_h = card_h + 40

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(canvas)

    session = await get_http_session()
    # Use medium-size images for drops (faster download, still looks good at 246x330)
    medium_urls = [card["image"].replace("/large/", "/medium/") if card.get("image") else card.get("image") for card in cards]
    tasks = [fetch_image(session, url) for url in medium_urls]
    raw_images = await asyncio.gather(*tasks)

    for i, card in enumerate(cards):
        x = 20 + i * (card_w + gap)
        y = 20
        rc = RARITY_COLORS.get(card["rarity"], (140, 155, 170))
        q_val = card.get("quality", "Good ⭐⭐")
        border_col = rc

        draw.rectangle([x, y, x + card_w, y + card_h], fill=(28, 30, 34, 255), outline=(60, 65, 75), width=3)
        draw.rectangle([x + 4, y + 4, x + card_w - 4, y + card_h - 4], outline=border_col, width=3)

        img_w, img_h = card_w - 14, card_h - 70
        resized_img = raw_images[i].resize((img_w, img_h), Image.Resampling.LANCZOS)
        
        if show_quality:
            # Apply Visual Quality Filter & artwork overlay effects
            filtered_img = apply_quality_filter_to_image(resized_img, q_val)
            canvas.paste(filtered_img, (x + 7, y + 7))
            apply_quality_effects_on_artwork(draw, x + 7, y + 7, img_w, img_h, q_val)
        else:
            # Hide quality before grab — show clean card with no badge
            canvas.paste(resized_img, (x + 7, y + 7))

        box_y1 = y + card_h - 70
        box_y2 = y + card_h - 6
        # Use rarity color with high opacity for the info box background
        rarity_bg = (rc[0], rc[1], rc[2], 220)
        draw.rectangle([x + 6, box_y1, x + card_w - 6, box_y2], fill=rarity_bg)
        # Bright accent bar on the left edge
        draw.line([x + 10, box_y1 + 8, x + 10, box_y2 - 8], fill=(255, 255, 255, 200), width=3)
        
        # Use larger fonts for text
        edition_text = f"ED 1 | #{card['temp_mint']}"
        id_text = f"ID: {card['code']}"
        char_disp = card['name'][:22]
        series_disp = card['series'][:22]

        # Measure text widths for right-alignment
        char_bbox = FONT_DROP_TITLE.getbbox(char_disp)
        char_tw = char_bbox[2] - char_bbox[0] if char_bbox else len(char_disp) * 9
        series_bbox = FONT_DROP_SUBTITLE.getbbox(series_disp)
        series_tw = series_bbox[2] - series_bbox[0] if series_bbox else len(series_disp) * 7

        # Top row: edition badge left, character name right
        draw.text((x + 18, box_y1 + 8), edition_text, fill=(255, 255, 255), font=FONT_DROP_BADGE)
        draw.text((max(x + 18, x + card_w - 14 - char_tw), box_y1 + 8), char_disp, fill=(255, 255, 255), font=FONT_DROP_TITLE)
        # Bottom row: card ID left, series name right
        draw.text((x + 18, box_y1 + 34), id_text, fill=(255, 255, 255, 220), font=FONT_DROP_SUBTITLE)
        draw.text((max(x + 18, x + card_w - 14 - series_tw), box_y1 + 34), series_disp, fill=(255, 255, 255, 200), font=FONT_DROP_SUBTITLE)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

async def render_single_card(card_data: dict) -> io.BytesIO:
    """Renders a single high-quality framed Karuta card for /card."""
    card_w, card_h = 340, 520
    canvas = Image.new("RGBA", (card_w, card_h), (18, 19, 22, 255))
    draw = ImageDraw.Draw(canvas)

    session = await get_http_session()
    raw_img = await fetch_image(session, card_data["image_url"])

    rc = RARITY_COLORS.get(card_data["rarity"], (140, 155, 170))
    q_val = card_data.get("quality", "Good ⭐⭐")
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

    box_y1 = card_h - 85
    box_y2 = card_h - 8
    # Use rarity color with high opacity for the info box background
    rarity_bg = (rc[0], rc[1], rc[2], 220)
    draw.rectangle([8, box_y1, card_w - 8, box_y2], fill=rarity_bg)
    # Bright accent bar on the left edge
    draw.line([14, box_y1 + 10, 14, box_y2 - 10], fill=(255, 255, 255, 200), width=4)

    edition_text = f"ED {card_data.get('edition', 1)} | #{card_data['mint_number']}"
    id_text = f"ID: {card_data['code'].upper()}"
    char_disp = card_data['character_name'][:22]
    series_disp = card_data['series_name'][:22]

    # Measure text widths for right-alignment
    char_bbox = FONT_SINGLE_TITLE.getbbox(char_disp)
    char_tw = char_bbox[2] - char_bbox[0] if char_bbox else len(char_disp) * 11
    series_bbox = FONT_SINGLE_SUBTITLE.getbbox(series_disp)
    series_tw = series_bbox[2] - series_bbox[0] if series_bbox else len(series_disp) * 9

    # Top row: edition badge left, character name right
    draw.text((24, box_y1 + 12), edition_text, fill=(255, 255, 255), font=FONT_SINGLE_BADGE)
    draw.text((max(24, card_w - 18 - char_tw), box_y1 + 12), char_disp, fill=(255, 255, 255), font=FONT_SINGLE_TITLE)
    # Bottom row: card ID left, series name right
    draw.text((24, box_y1 + 42), id_text, fill=(255, 255, 255, 220), font=FONT_SINGLE_SUBTITLE)
    draw.text((max(24, card_w - 18 - series_tw), box_y1 + 42), series_disp, fill=(255, 255, 255, 200), font=FONT_SINGLE_SUBTITLE)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

render_three_cards_composite = render_cards_image
