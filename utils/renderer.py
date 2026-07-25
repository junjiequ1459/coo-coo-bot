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
    """Load a scalable font while preserving the requested pixel size."""
    if bold:
        font_paths = [
            "/System/Library/Fonts/Supplemental/Trebuchet MS Bold.ttf",
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Avenir Next.ttc",
            "/System/Library/Fonts/Supplemental/Futura.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    else:
        font_paths = [
            "/System/Library/Fonts/Supplemental/Trebuchet MS.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Avenir Next.ttc",
            "/System/Library/Fonts/Supplemental/Futura.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    # Pillow's scalable bundled font keeps text at the intended size even on
    # minimal hosts (such as Railway images) that contain no system fonts.
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()

def _load_monospace_font(size):
    """Load clean monospace font for Card Code and Edition numbers."""
    mono_paths = [
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
        "/System/Library/Fonts/Supplemental/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Monaco.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    ]
    for fp in mono_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return _load_font(size, bold=True)

# Pre-load clean fonts at sizes that match the card proportions.
FONT_TITLE_DROP = _load_font(34, bold=True)
FONT_SERIES_DROP = _load_font(18, bold=True)
FONT_BADGE_DROP = _load_monospace_font(15)

FONT_TITLE_SINGLE = _load_font(40, bold=True)
FONT_SERIES_SINGLE = _load_font(21, bold=True)
FONT_BADGE_SINGLE = _load_monospace_font(17)


def _fit_font_to_width(font, text: str, max_width: int, min_size: int):
    """Shrink a scalable font only when a long name would clip the card."""
    bbox = font.getbbox(text)
    if not bbox or bbox[2] - bbox[0] <= max_width:
        return font

    current_size = getattr(font, "size", min_size)
    target_size = max(min_size, int(current_size * max_width / (bbox[2] - bbox[0])))
    try:
        return font.font_variant(size=target_size)
    except (AttributeError, OSError):
        return font

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
    """Scales artwork image top-aligned to fill 100% of the card canvas edge-to-edge."""
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

def _draw_rainbow_line(target_img: Image.Image, box: tuple):
    """Draws a smooth rainbow gradient horizontal line."""
    bx1, by1, bx2, by2 = box
    w = max(1, bx2 - bx1)
    h = max(1, by2 - by1)
    
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
    
    for col in range(w):
        t = col / max(1, w - 1)
        idx = t * (num_c - 1)
        i1 = int(idx) % num_c
        i2 = min(i1 + 1, num_c - 1)
        frac = idx - int(idx)
        
        r = int(colors[i1][0] + (colors[i2][0] - colors[i1][0]) * frac)
        g = int(colors[i1][1] + (colors[i2][1] - colors[i1][1]) * frac)
        b = int(colors[i1][2] + (colors[i2][2] - colors[i1][2]) * frac)
        rb_draw.line([(col, 0), (col, h)], fill=(r, g, b, 255))
            
    target_img.paste(rainbow, (bx1, by1), rainbow)

# ==========================================
# 🖼️ DRAW CARD (Silver Metallic Border Design)
# ==========================================
def draw_card_on_canvas(canvas: Image.Image, x: int, y: int, card_w: int, card_h: int,
                        raw_img: Image.Image, card_data: dict, font_title, font_series, font_badge):
    """Draws a card with a sleek 3D silver-gray metallic outer border matching the user's mockup."""
    draw = ImageDraw.Draw(canvas)
    rarity_str = str(card_data.get("rarity", "Legendary")).lower()

    # 1. Thick 3D Silver-Gray Metallic Outer Frame
    frame_width = max(18, round(card_w * 0.06))
    frame_r = max(20, round(card_w * 0.075))
    frame_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    f_draw = ImageDraw.Draw(frame_img)

    # Broad gray bands with bright bevels create the heavy frame from the
    # reference card without washing the border out to white.
    f_draw.rounded_rectangle(
        [0, 0, card_w - 1, card_h - 1],
        radius=frame_r,
        fill=(54, 58, 65),
        outline=(16, 17, 20),
        width=2,
    )
    f_draw.rounded_rectangle(
        [2, 2, card_w - 3, card_h - 3],
        radius=frame_r - 2,
        fill=(174, 180, 190),
        outline=(224, 228, 235),
        width=2,
    )
    f_draw.rounded_rectangle(
        [6, 6, card_w - 7, card_h - 7],
        radius=frame_r - 6,
        fill=(116, 122, 132),
        outline=(92, 97, 106),
        width=2,
    )
    f_draw.rounded_rectangle(
        [10, 10, card_w - 11, card_h - 11],
        radius=frame_r - 10,
        fill=(48, 52, 60),
        outline=(202, 207, 216),
        width=2,
    )

    pad = frame_width
    view_x, view_y = pad, pad
    view_w, view_h = card_w - pad * 2, card_h - pad * 2

    # Inner Viewport Box Fill (Neutral dark border, no colored accent)
    f_draw.rounded_rectangle([view_x - 3, view_y - 3, view_x + view_w + 2, view_y + view_h + 2],
                             radius=11, fill=(28, 30, 35), outline=(8, 9, 11), width=2)
    f_draw.rounded_rectangle([view_x, view_y, view_x + view_w - 1, view_y + view_h - 1],
                             radius=8, fill=(18, 19, 22), outline=(73, 78, 87), width=1)

    canvas.paste(frame_img, (x, y), frame_img)

    content_x = x + view_x
    content_y = y + view_y
    content_w = view_w
    content_h = view_h

    # 2. Artwork Viewport (Fills 100% of inner content box)
    fitted_art = fit_artwork_image(raw_img, content_w, content_h)

    # Rounded corners mask for inner content box
    art_mask = Image.new("L", (content_w, content_h), 0)
    art_mask_draw = ImageDraw.Draw(art_mask)
    art_mask_draw.rounded_rectangle([0, 0, content_w - 1, content_h - 1], radius=8, fill=255)

    canvas.paste(fitted_art, (content_x, content_y), art_mask)

    # 3. Bottom Dark Overlay Container Section
    bot_h = int(content_h * 0.34)
    bot_y = content_y + content_h - bot_h

    bot_overlay = Image.new("RGBA", (content_w, bot_h), (0, 0, 0, 0))
    bo_draw = ImageDraw.Draw(bot_overlay)
    
    # Solid dark container background covering bottom portion of artwork
    bo_draw.rectangle([0, 0, content_w - 1, bot_h - 1], fill=(18, 19, 22, 245))

    canvas.paste(bot_overlay, (content_x, bot_y), bot_overlay)

    # 4. Series Name & Rarity Accent Line (Only the series lines take rarity color)
    series_name = card_data.get("series", card_data.get("series_name", "Genshin Impact"))[:24]
    font_series = _fit_font_to_width(font_series, series_name, content_w - 48, 14)
    s_bbox = font_series.getbbox(series_name)
    s_tw = s_bbox[2] - s_bbox[0] if s_bbox else len(series_name) * 8
    s_th = s_bbox[3] - s_bbox[1] if s_bbox else 14

    sy = bot_y + 12
    line_y = sy + s_th // 2
    margin = 14
    left_line_x1 = content_x + margin
    left_line_x2 = content_x + (content_w - s_tw) // 2 - 8
    right_line_x1 = content_x + (content_w + s_tw) // 2 + 8
    right_line_x2 = content_x + content_w - margin

    is_mythic = "mythic" in rarity_str
    if is_mythic:
        if left_line_x2 > left_line_x1:
            _draw_rainbow_line(canvas, (left_line_x1, line_y, left_line_x2, line_y + 1))
        if right_line_x2 > right_line_x1:
            _draw_rainbow_line(canvas, (right_line_x1, line_y, right_line_x2, line_y + 1))
    elif "legendary" in rarity_str or "legend" in rarity_str:
        line_color = (255, 215, 0, 220)       # Gold
        if left_line_x2 > left_line_x1:
            draw.line([(left_line_x1, line_y), (left_line_x2, line_y)], fill=line_color, width=1)
        if right_line_x2 > right_line_x1:
            draw.line([(right_line_x1, line_y), (right_line_x2, line_y)], fill=line_color, width=1)
    elif "epic" in rarity_str:
        line_color = (147, 112, 219, 220)     # Rich Purple
        if left_line_x2 > left_line_x1:
            draw.line([(left_line_x1, line_y), (left_line_x2, line_y)], fill=line_color, width=1)
        if right_line_x2 > right_line_x1:
            draw.line([(right_line_x1, line_y), (right_line_x2, line_y)], fill=line_color, width=1)
    elif "rare" in rarity_str:
        line_color = (0, 229, 255, 220)       # Cyan Blue
        if left_line_x2 > left_line_x1:
            draw.line([(left_line_x1, line_y), (left_line_x2, line_y)], fill=line_color, width=1)
        if right_line_x2 > right_line_x1:
            draw.line([(right_line_x1, line_y), (right_line_x2, line_y)], fill=line_color, width=1)
    else:
        line_color = (140, 155, 170, 220)     # Slate Silver (Common)
        if left_line_x2 > left_line_x1:
            draw.line([(left_line_x1, line_y), (left_line_x2, line_y)], fill=line_color, width=1)
        if right_line_x2 > right_line_x1:
            draw.line([(right_line_x1, line_y), (right_line_x2, line_y)], fill=line_color, width=1)

    sx = content_x + (content_w - s_tw) // 2
    draw.text((sx, sy), series_name, fill=(230, 235, 245), font=font_series)

    # Character Name
    char_name = card_data.get("name", card_data.get("character_name", "Citlali"))[:20]
    font_title = _fit_font_to_width(font_title, char_name, content_w - 24, 22)
    c_bbox = font_title.getbbox(char_name)
    c_tw = c_bbox[2] - c_bbox[0] if c_bbox else len(char_name) * 14
    c_th = c_bbox[3] - c_bbox[1] if c_bbox else 24
    nx = content_x + (content_w - c_tw) // 2
    ny = sy + s_th + 4
    draw.text(
        (nx, ny),
        char_name,
        fill=(248, 249, 252),
        font=font_title,
        stroke_width=2,
        stroke_fill=(6, 7, 9, 230),
    )

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
    cp_draw.rounded_rectangle([0, 0, badge_pw - 1, badge_ph - 1], radius=6, fill=(0, 0, 0, 240), outline=(40, 40, 40), width=1)
    cp_draw.text(((badge_pw - code_tw) // 2, (badge_ph - code_th) // 2 - 1), card_code, fill=(255, 215, 0), font=font_badge)
    canvas.paste(code_pill, (badge_px, badge_py), code_pill)

    ed_bbox = font_badge.getbbox(edition_str)
    ed_tw = ed_bbox[2] - ed_bbox[0] if ed_bbox else len(edition_str) * 7
    ed_th = ed_bbox[3] - ed_bbox[1] if ed_bbox else 12

    ed_pw = ed_tw + 16
    ed_ph = ed_th + 6
    ed_px = content_x + content_w - ed_pw - 12
    ed_py = badge_py

    ed_pill = Image.new("RGBA", (ed_pw, ed_ph), (0, 0, 0, 0))
    ep_draw = ImageDraw.Draw(ed_pill)
    ep_draw.rounded_rectangle([0, 0, ed_pw - 1, ed_ph - 1], radius=6, fill=(0, 0, 0, 240), outline=(40, 40, 40), width=1)
    ep_draw.text(((ed_pw - ed_tw) // 2, (ed_ph - ed_th) // 2 - 1), edition_str, fill=(255, 215, 0), font=font_badge)
    canvas.paste(ed_pill, (ed_px, ed_py), ed_pill)

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
