import io
import os
import math
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# ==========================================
# 🔤 FONT LOADING
# ==========================================
def _load_font(size, bold=True):
    """Load clean bold fonts for card title and series text."""
    if bold:
        font_paths = [
            "/System/Library/Fonts/Supplemental/Trebuchet MS Bold.ttf",
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Avenir Next.ttc",
            "/System/Library/Fonts/Supplemental/Futura.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        font_paths = [
            "/System/Library/Fonts/Supplemental/Trebuchet MS.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Avenir Next.ttc",
            "/System/Library/Fonts/Supplemental/Futura.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()

def _load_monospace_font(size):
    """Load clean monospace font for Card Code and Edition numbers."""
    mono_paths = [
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
        "/System/Library/Fonts/Supplemental/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Monaco.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ]
    for fp in mono_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return _load_font(size, bold=True)

# Pre-load clean fonts
FONT_TITLE_DROP = _load_font(27, bold=True)
FONT_SERIES_DROP = _load_font(13, bold=False)
FONT_BADGE_DROP = _load_monospace_font(11)

FONT_TITLE_SINGLE = _load_font(33, bold=True)
FONT_SERIES_SINGLE = _load_font(15, bold=False)
FONT_BADGE_SINGLE = _load_monospace_font(13)

# Shared aiohttp session
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
    img = Image.new("RGBA", (280, 420), (32, 34, 37, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 270, 410], outline=(70, 75, 85), width=2)
    draw.text((40, 200), "Image Unavailable", fill=(160, 175, 190))
    return img

def fit_artwork_image(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scales artwork image proportionally top-aligned so it fills the viewport edge-to-edge without distortion."""
    orig_w, orig_h = img.size
    if orig_w == 0 or orig_h == 0:
        return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    scale = max(target_w / orig_w, target_h / orig_h)
    new_w = max(target_w, int(orig_w * scale))
    new_h = max(target_h, int(orig_h * scale))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    left = (new_w - target_w) // 2
    top = 0
    return resized.crop((left, top, left + target_w, top + target_h))

def _round_corners(img: Image.Image, radius: int) -> Image.Image:
    """Apply rounded corners to an RGBA image using an alpha mask."""
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=radius, fill=255)
    out = img.copy()
    out.putalpha(mask)
    return out

def _draw_rainbow_border(target_img: Image.Image, box: tuple, radius: int = 10, width: int = 2):
    """Draws a vibrant linear rainbow gradient rounded border."""
    bx1, by1, bx2, by2 = box
    w = max(1, bx2 - bx1)
    h = max(1, by2 - by1)
    
    if w <= width * 2 or h <= width * 2:
        return

    rainbow = Image.new("RGBA", (w, h))
    rb_draw = ImageDraw.Draw(rainbow)
    
    colors = [
        (255, 60, 60),    # Red
        (255, 160, 40),   # Orange
        (255, 230, 50),   # Yellow
        (60, 230, 110),   # Green
        (40, 200, 255),   # Cyan
        (160, 80, 255),   # Violet
        (255, 90, 200),   # Pink
    ]
    num_c = len(colors)
    
    for row in range(h):
        for col in range(w):
            t = (row / max(1, h) + col / max(1, w)) / 2.0
            idx = t * (num_c - 1)
            i1 = int(idx) % num_c
            i2 = min(i1 + 1, num_c - 1)
            frac = idx - int(idx)
            
            r = int(colors[i1][0] + (colors[i2][0] - colors[i1][0]) * frac)
            g = int(colors[i1][1] + (colors[i2][1] - colors[i1][1]) * frac)
            b = int(colors[i1][2] + (colors[i2][2] - colors[i1][2]) * frac)
            rb_draw.point((col, row), fill=(r, g, b, 255))
            
    # Mask to outline stroke
    mask_outer = Image.new("L", (w, h), 0)
    d_out = ImageDraw.Draw(mask_outer)
    d_out.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    
    mask_inner = Image.new("L", (w, h), 0)
    d_in = ImageDraw.Draw(mask_inner)
    in_rad = max(0, radius - width)
    d_in.rounded_rectangle([width, width, w - 1 - width, h - 1 - width], radius=in_rad, fill=255)
    
    stroke_mask = Image.new("L", (w, h), 0)
    for row in range(h):
        for col in range(w):
            val_out = mask_outer.getpixel((col, row))
            val_in = mask_inner.getpixel((col, row))
            stroke_mask.putpixel((col, row), max(0, val_out - val_in))
            
    target_img.paste(rainbow, (bx1, by1), stroke_mask)

# ==========================================
# 🖼️ DRAW CARD (Exact Match to User Mockup)
# ==========================================
def draw_card_on_canvas(canvas: Image.Image, x: int, y: int, card_w: int, card_h: int,
                        raw_img: Image.Image, card_data: dict, font_title, font_series, font_badge):
    """Draws a card matching mockup, featuring a dynamic rainbow gradient inner border for Mythic cards."""
    draw = ImageDraw.Draw(canvas)
    rarity_str = str(card_data.get("rarity", "Legendary")).lower()

    # 1. Metallic Outer Frame
    frame_r = 16
    frame_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    f_draw = ImageDraw.Draw(frame_img)

    f_draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=frame_r, fill=(28, 30, 36), outline=(90, 95, 110), width=2)
    f_draw.rounded_rectangle([2, 2, card_w - 3, card_h - 3], radius=frame_r - 2, fill=(22, 24, 28), outline=(180, 185, 200), width=2)

    pad = 12
    view_x, view_y = pad, pad
    view_w, view_h = card_w - pad * 2, card_h - pad * 2

    # Inner Viewport Box Fill
    f_draw.rounded_rectangle([view_x, view_y, view_x + view_w - 1, view_y + view_h - 1],
                             radius=8, fill=(18, 19, 22))

    # 2. Inner Viewport Accent Border (Rainbow for Mythic, Gold for Legendary, etc.)
    is_mythic = "mythic" in rarity_str
    if is_mythic:
        _draw_rainbow_border(frame_img, (view_x - 2, view_y - 2, view_x + view_w + 1, view_y + view_h + 1), radius=10, width=2)
        accent_line = (255, 160, 200, 220)
    elif "legendary" in rarity_str or "legend" in rarity_str:
        f_draw.rounded_rectangle([view_x - 2, view_y - 2, view_x + view_w + 1, view_y + view_h + 1],
                                 radius=10, outline=(255, 220, 100), width=2)
        accent_line = (180, 150, 60, 180)
    elif "epic" in rarity_str:
        f_draw.rounded_rectangle([view_x - 2, view_y - 2, view_x + view_w + 1, view_y + view_h + 1],
                                 radius=10, outline=(190, 120, 255), width=2)
        accent_line = (160, 80, 230, 180)
    else:
        f_draw.rounded_rectangle([view_x - 2, view_y - 2, view_x + view_w + 1, view_y + view_h + 1],
                                 radius=10, outline=(110, 170, 255), width=2)
        accent_line = (80, 140, 230, 180)

    canvas.paste(frame_img, (x, y), frame_img)

    content_x = x + view_x
    content_y = y + view_y
    content_w = view_w
    content_h = view_h

    # 3. Artwork Viewport (Occupies top ~75% of inner content box)
    art_h = int(content_h * 0.75)
    fitted_art = fit_artwork_image(raw_img, content_w, art_h)

    art_mask = Image.new("L", (content_w, art_h), 255)
    art_mask_draw = ImageDraw.Draw(art_mask)
    art_mask_draw.rectangle([0, 8, content_w, art_h], fill=255)
    art_mask_draw.rounded_rectangle([0, 0, content_w - 1, art_h - 1], radius=8, fill=255)

    canvas.paste(fitted_art, (content_x, content_y), art_mask)

    # 4. Bottom Dark Container Section
    bot_y = content_y + art_h

    series_name = card_data.get("series", card_data.get("series_name", "Genshin Impact"))[:24]
    s_bbox = font_series.getbbox(series_name)
    s_tw = s_bbox[2] - s_bbox[0] if s_bbox else len(series_name) * 8
    s_th = s_bbox[3] - s_bbox[1] if s_bbox else 14

    sy = bot_y + 14
    line_y = sy + s_th // 2
    margin = 14
    left_line_x1 = content_x + margin
    left_line_x2 = content_x + (content_w - s_tw) // 2 - 8
    right_line_x1 = content_x + (content_w + s_tw) // 2 + 8
    right_line_x2 = content_x + content_w - margin

    if left_line_x2 > left_line_x1:
        draw.line([(left_line_x1, line_y), (left_line_x2, line_y)], fill=accent_line, width=1)
    if right_line_x2 > right_line_x1:
        draw.line([(right_line_x1, line_y), (right_line_x2, line_y)], fill=accent_line, width=1)

    sx = content_x + (content_w - s_tw) // 2
    draw.text((sx, sy), series_name, fill=(230, 235, 245), font=font_series)

    char_name = card_data.get("name", card_data.get("character_name", "Citlali"))[:20]
    c_bbox = font_title.getbbox(char_name)
    c_tw = c_bbox[2] - c_bbox[0] if c_bbox else len(char_name) * 14
    c_th = c_bbox[3] - c_bbox[1] if c_bbox else 24
    nx = content_x + (content_w - c_tw) // 2
    ny = sy + s_th + 4
    draw.text((nx + 1, ny + 1), char_name, fill=(0, 0, 0, 180), font=font_title)
    draw.text((nx, ny), char_name, fill=(255, 255, 255), font=font_title)

    # 5. Bottom Row: Left Pill Code Badge & Right Print/Edition Text
    card_code = str(card_data.get("code", "VL9BSJ3")).upper()
    mint_val = card_data.get("temp_mint", card_data.get("mint_number", 912))
    ed_val = card_data.get("edition", 2)
    edition_str = f"#{mint_val} · ED {ed_val}"

    code_bbox = font_badge.getbbox(card_code)
    code_tw = code_bbox[2] - code_bbox[0] if code_bbox else len(card_code) * 7
    code_th = code_bbox[3] - code_bbox[1] if code_bbox else 12

    badge_pw = code_tw + 16
    badge_ph = code_th + 6
    badge_px = content_x + 12
    badge_py = content_y + content_h - badge_ph - 10

    code_pill = Image.new("RGBA", (badge_pw, badge_ph), (0, 0, 0, 0))
    cp_draw = ImageDraw.Draw(code_pill)
    cp_draw.rounded_rectangle([0, 0, badge_pw - 1, badge_ph - 1], radius=6, fill=(32, 35, 42), outline=(55, 60, 72), width=1)
    cp_draw.text(((badge_pw - code_tw) // 2, (badge_ph - code_th) // 2 - 1), card_code, fill=(220, 225, 235), font=font_badge)
    canvas.paste(code_pill, (badge_px, badge_py), code_pill)

    ed_bbox = font_badge.getbbox(edition_str)
    ed_tw = ed_bbox[2] - ed_bbox[0] if ed_bbox else len(edition_str) * 7
    ed_th = ed_bbox[3] - ed_bbox[1] if ed_bbox else 12
    ed_px = content_x + content_w - ed_tw - 12
    ed_py = badge_py + (badge_ph - ed_th) // 2
    draw.text((ed_px, ed_py), edition_str, fill=(170, 175, 190), font=font_badge)

# ==========================================
# 🃏 RENDER DROP CARDS (3 side-by-side)
# ==========================================
async def render_cards_image(cards: list, show_quality: bool = False) -> io.BytesIO:
    """Renders 3 cards side-by-side for /drop."""
    card_w, card_h = 280, 450
    gap = 18
    pad = 20

    canvas_w = (card_w * 3) + (gap * 2) + (pad * 2)
    canvas_h = card_h + (pad * 2)

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (14, 15, 18, 255))

    session = await get_http_session()
    medium_urls = [card["image"].replace("/large/", "/medium/") if card.get("image") else card.get("image") for card in cards]
    tasks = [fetch_image(session, url) for url in medium_urls]
    raw_images = await asyncio.gather(*tasks)

    for i, card in enumerate(cards):
        cx = pad + i * (card_w + gap)
        cy = pad
        draw_card_on_canvas(canvas, cx, cy, card_w, card_h, raw_images[i], card,
                            FONT_TITLE_DROP, FONT_SERIES_DROP, FONT_BADGE_DROP)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ==========================================
# 🃏 RENDER SINGLE CARD (view/lookup)
# ==========================================
async def render_single_card(card_data: dict) -> io.BytesIO:
    """Renders a single card for /card."""
    card_w, card_h = 320, 500
    pad = 20

    canvas_w = card_w + pad * 2
    canvas_h = card_h + pad * 2

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (14, 15, 18, 0))

    session = await get_http_session()
    raw_img = await fetch_image(session, card_data["image_url"])

    draw_card_on_canvas(canvas, pad, pad, card_w, card_h, raw_img, card_data,
                        FONT_TITLE_SINGLE, FONT_SERIES_SINGLE, FONT_BADGE_SINGLE)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ==========================================
# 🎨 RENDER FULL-ART UNFRAMED CARD
# ==========================================
async def render_full_art_card(card_data: dict, custom_frame: Image.Image = None) -> io.BytesIO:
    """Renders a full-bleed unframed card (100% artwork canvas), ready for custom shop borders."""
    card_w, card_h = 320, 500
    corner_r = 12

    canvas = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    session = await get_http_session()
    raw_img = await fetch_image(session, card_data["image_url"])

    fitted_art = fit_artwork_image(raw_img, card_w, card_h)
    canvas.paste(fitted_art, (0, 0))

    vignette = Image.new("RGBA", (card_w, card_h))
    v_draw = ImageDraw.Draw(vignette)
    for y in range(card_h - 110, card_h):
        t = (y - (card_h - 110)) / 110
        alpha = int(180 * t)
        v_draw.line([(0, y), (card_w, y)], fill=(0, 0, 0, alpha))

    canvas.paste(vignette, (0, 0), vignette)

    if custom_frame:
        resized_frame = fit_artwork_image(custom_frame, card_w, card_h)
        canvas.paste(resized_frame, (0, 0), resized_frame)

    series_name = card_data.get("series_name", card_data.get("series", "Genshin Impact"))[:24]
    s_bbox = FONT_SERIES_SINGLE.getbbox(series_name)
    s_tw = s_bbox[2] - s_bbox[0] if s_bbox else len(series_name) * 13
    s_th = s_bbox[3] - s_bbox[1] if s_bbox else 22
    sx = (card_w - s_tw) // 2
    sy = card_h - 85
    draw.text((sx + 2, sy + 2), series_name, fill=(0, 0, 0, 220), font=FONT_SERIES_SINGLE)
    draw.text((sx, sy), series_name, fill=(255, 235, 170), font=FONT_SERIES_SINGLE)

    char_name = card_data.get("character_name", card_data.get("name", "Citlali"))[:22]
    c_bbox = FONT_TITLE_SINGLE.getbbox(char_name)
    c_tw = c_bbox[2] - c_bbox[0] if c_bbox else len(char_name) * 16
    c_th = c_bbox[3] - c_bbox[1] if c_bbox else 30
    nx = (card_w - c_tw) // 2
    ny = sy + s_th + 4
    draw.text((nx + 2, ny + 2), char_name, fill=(0, 0, 0, 220), font=FONT_TITLE_SINGLE)
    draw.text((nx, ny), char_name, fill=(255, 255, 255), font=FONT_TITLE_SINGLE)

    canvas = _round_corners(canvas, corner_r)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

render_three_cards_composite = render_cards_image
