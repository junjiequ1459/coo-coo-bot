import io
import os
import math
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from config import RARITY_COLORS

# ==========================================
# 🔤 FONT LOADING
# ==========================================
def _load_font(size, bold=True):
    """Try to load a clean, bold font for authentic Karuta card text."""
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
    """Load a clean monospace font for top/bottom badges (Card Code & Print Numbers)."""
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

# Pre-load fonts with prominent sizes
FONT_TITLE_DROP = _load_font(30, bold=True)
FONT_SERIES_DROP = _load_font(23, bold=True)
FONT_BADGE_DROP = _load_monospace_font(13)

FONT_TITLE_SINGLE = _load_font(34, bold=True)
FONT_SERIES_SINGLE = _load_font(26, bold=True)
FONT_BADGE_SINGLE = _load_monospace_font(15)

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

# ==========================================
# 📷 QUALITY FILTERS & EFFECTS
# ==========================================
def apply_quality_filter_to_image(img: Image.Image, quality_str: str) -> Image.Image:
    """Applies visual quality wear filters scaled by tier."""
    q_clean = str(quality_str).lower()

    if "mint" in q_clean or "⭐⭐⭐⭐" in q_clean:
        return img
    elif "excellent" in q_clean or "⭐⭐⭐" in q_clean:
        enhancer = ImageEnhance.Color(img)
        return enhancer.enhance(0.85)
    elif "good" in q_clean or "⭐⭐" in q_clean:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.70)
        enhancer_b = ImageEnhance.Brightness(img)
        return enhancer_b.enhance(0.95)
    elif "poor" in q_clean or (q_clean.startswith("poor") and "⭐⭐" not in q_clean):
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.35)
        enhancer_b = ImageEnhance.Brightness(img)
        img = enhancer_b.enhance(0.82)
        enhancer_c = ImageEnhance.Contrast(img)
        img = enhancer_c.enhance(1.20)
        overlay = Image.new("RGBA", img.size, (130, 95, 60, 60))
        return Image.alpha_composite(img.convert("RGBA"), overlay)
    elif "damaged" in q_clean or "❌" in q_clean:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.20)
        enhancer_b = ImageEnhance.Brightness(img)
        return enhancer_b.enhance(0.75)

    return img

def apply_quality_effects_on_artwork(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, quality_str: str):
    """Draws physical scratches and shattered glass corner cracks on artwork."""
    q_clean = str(quality_str).lower()

    if "poor" in q_clean or "damaged" in q_clean or "❌" in q_clean:
        scratch_col = (200, 200, 200, 110)
        draw.line([x + 12, y + 25, x + 65, y + 70], fill=scratch_col, width=1)
        draw.line([x + w - 40, y + h - 90, x + w - 15, y + h - 35], fill=scratch_col, width=1)
        draw.line([x + 30, y + h - 50, x + 90, y + h - 20], fill=scratch_col, width=1)

    if "damaged" in q_clean or "❌" in q_clean:
        crack_col = (235, 235, 245, 170)
        tl_x, tl_y = x + 4, y + 4
        draw.line([tl_x, tl_y, tl_x + 35, tl_y + 25], fill=crack_col, width=2)
        draw.line([tl_x + 35, tl_y + 25, tl_x + 55, tl_y + 15], fill=crack_col, width=1)
        br_x, br_y = x + w - 4, y + h - 4
        draw.line([br_x, br_y, br_x - 45, br_y - 30], fill=crack_col, width=2)
        draw.line([br_x - 45, br_y - 30, br_x - 70, br_y - 20], fill=crack_col, width=1)

def fit_and_crop_image(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Center-crops and scales an image to fill target dimensions (object-fit: cover)."""
    orig_w, orig_h = img.size
    if orig_w == 0 or orig_h == 0:
        return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    scale = max(target_w / orig_w, target_h / orig_h)
    new_w = max(target_w, int(orig_w * scale))
    new_h = max(target_h, int(orig_h * scale))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))

# ==========================================
# 👑 GOLD BANNER GENERATOR (TALLER VERTICAL)
# ==========================================
def _create_gold_banner(w: int, h: int, arch_type: str = "top") -> Image.Image:
    """Generates a smooth golden gradient banner with a curved arch notch edge."""
    banner = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bg = Image.new("RGBA", (w, h))
    bg_draw = ImageDraw.Draw(bg)

    # Smooth Golden yellow gradient background
    for row in range(h):
        t = row / max(h - 1, 1)
        r = int(255 + (245 - 255) * t)
        g = int(235 + (190 - 235) * t)
        b = int(125 + (75 - 125) * t)
        bg_draw.line([(0, row), (w, row)], fill=(r, g, b, 255))

    # Arch mask logic:
    mask = Image.new("L", (w, h), 255)
    mask_draw = ImageDraw.Draw(mask)

    arch_w = int(w * 0.62)
    arch_x1 = (w - arch_w) // 2
    arch_x2 = arch_x1 + arch_w
    notch_depth = 16

    if arch_type == "top":
        cut_poly = [
            (0, h), (w, h),
            (w, h - 8),
            (arch_x2 + 12, h - 8),
            (arch_x2 - 12, h - notch_depth),
            (arch_x1 + 12, h - notch_depth),
            (arch_x1 - 12, h - 8),
            (0, h - 8)
        ]
        mask_draw.polygon(cut_poly, fill=0)

    elif arch_type == "bottom":
        cut_poly = [
            (0, 0), (w, 0),
            (w, 8),
            (arch_x2 + 12, 8),
            (arch_x2 - 12, notch_depth),
            (arch_x1 + 12, notch_depth),
            (arch_x1 - 12, 8),
            (0, 8)
        ]
        mask_draw.polygon(cut_poly, fill=0)

    banner.paste(bg, (0, 0), mask)
    b_draw = ImageDraw.Draw(banner)

    # 3D Golden Bevel Border framing the cutout curve
    if arch_type == "top":
        b_draw.line([(0, h - 8), (arch_x1 - 12, h - 8)], fill=(195, 145, 30), width=3)
        b_draw.line([(arch_x1 - 12, h - 8), (arch_x1 + 12, h - notch_depth)], fill=(195, 145, 30), width=3)
        b_draw.line([(arch_x1 + 12, h - notch_depth), (arch_x2 - 12, h - notch_depth)], fill=(255, 245, 175), width=3)
        b_draw.line([(arch_x2 - 12, h - notch_depth), (arch_x2 + 12, h - 8)], fill=(195, 145, 30), width=3)
        b_draw.line([(arch_x2 + 12, h - 8), (w, h - 8)], fill=(195, 145, 30), width=3)
    else:
        b_draw.line([(0, 8), (arch_x1 - 12, 8)], fill=(255, 245, 175), width=3)
        b_draw.line([(arch_x1 - 12, 8), (arch_x1 + 12, notch_depth)], fill=(255, 245, 175), width=3)
        b_draw.line([(arch_x1 + 12, notch_depth), (arch_x2 - 12, notch_depth)], fill=(195, 145, 30), width=3)
        b_draw.line([(arch_x2 - 12, notch_depth), (arch_x2 + 12, 8)], fill=(255, 245, 175), width=3)
        b_draw.line([(arch_x2 + 12, 8), (w, 8)], fill=(255, 245, 175), width=3)

    return banner

# ==========================================
# 🛡️ KARUTA FULL RECTANGULAR METALLIC FRAME
# ==========================================
def _draw_karuta_frame_structure(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int):
    """Draws full metallic frame extending all the way to outer edges without chamfer corner cutouts."""
    t_frame = 14

    # Layer 1: Frame Outer Rectangular Fill (Extends all the way to corners)
    draw.rectangle([x, y, x + w, y + h], fill=(168, 173, 183))

    # Inner Viewport Box
    inner_x, inner_y = x + t_frame, y + t_frame
    inner_w, inner_h = w - t_frame * 2, h - t_frame * 2
    draw.rectangle([inner_x, inner_y, inner_x + inner_w, inner_y + inner_h], fill=(22, 24, 28))

    # Layer 2: Outer Dark Rectangular Bevel Outline
    draw.rectangle([x, y, x + w, y + h], outline=(42, 45, 52), width=2)

    # Layer 3: Metallic Bevel Highlights (Full Edge Alignment)
    draw.line([(x + 2, y + 2), (x + w - 2, y + 2)], fill=(240, 245, 255), width=2)
    draw.line([(x + 2, y + 2), (x + 2, y + h - 2)], fill=(235, 240, 250), width=2)

    draw.line([(x + 2, y + h - 2), (x + w - 2, y + h - 2)], fill=(85, 88, 96), width=2)
    draw.line([(x + w - 2, y + 2), (x + w - 2, y + h - 2)], fill=(85, 88, 96), width=2)

    # Inner Inset Border
    draw.rectangle([inner_x, inner_y, inner_x + inner_w, inner_y + inner_h],
                   outline=(50, 53, 60), width=2)

    # Corner Metal Plate Accents & Rivets
    # Top-Left
    draw.ellipse([x + 10, y + 10, x + 14, y + 14], fill=(220, 225, 235), outline=(60, 65, 75))
    # Top-Right
    draw.ellipse([x + w - 14, y + 10, x + w - 10, y + 14], fill=(220, 225, 235), outline=(60, 65, 75))
    # Bottom-Left
    draw.ellipse([x + 10, y + h - 14, x + 14, y + h - 10], fill=(220, 225, 235), outline=(60, 65, 75))
    # Bottom-Right
    draw.ellipse([x + w - 14, y + h - 14, x + w - 10, y + h - 10], fill=(220, 225, 235), outline=(60, 65, 75))

    # Side Recessed Notches with Silver Rivets
    notch_cy = y + h // 2
    notch_h = 32
    notch_w = 6
    draw.rectangle([x, notch_cy - notch_h // 2, x + notch_w, notch_cy + notch_h // 2],
                   fill=(55, 58, 65), outline=(35, 38, 45), width=1)
    draw.ellipse([x + 1, notch_cy - 10, x + 5, notch_cy - 6], fill=(210, 215, 225))
    draw.ellipse([x + 1, notch_cy + 6, x + 5, notch_cy + 10], fill=(210, 215, 225))

    draw.rectangle([x + w - notch_w, notch_cy - notch_h // 2, x + w, notch_cy + notch_h // 2],
                   fill=(55, 58, 65), outline=(35, 38, 45), width=1)
    draw.ellipse([x + w - 5, notch_cy - 10, x + w - 1, notch_cy - 6], fill=(210, 215, 225))
    draw.ellipse([x + w - 5, notch_cy + 6, x + w - 1, notch_cy + 10], fill=(210, 215, 225))


def _draw_karuta_badges(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int,
                        card_code: str, mint_text: str, font_badge):
    """Draws top header badge (Card Code) and bottom footer badge (Print & Edition)."""
    # Top Code Badge
    bw, bh = 116, 22
    bx = x + (w - bw) // 2
    by = y + 1
    badge_poly = [
        (bx + 8, by),
        (bx + bw - 8, by),
        (bx + bw, by + 8),
        (bx + bw - 4, by + bh),
        (bx + 4, by + bh),
        (bx, by + 8)
    ]
    draw.polygon(badge_poly, fill=(18, 19, 22), outline=(75, 80, 90), width=1)

    code_str = str(card_code).upper()
    c_bbox = font_badge.getbbox(code_str)
    c_tw = c_bbox[2] - c_bbox[0] if c_bbox else len(code_str) * 8
    c_th = c_bbox[3] - c_bbox[1] if c_bbox else 12
    draw.text((bx + (bw - c_tw) // 2, by + (bh - c_th) // 2 - 1),
              code_str, fill=(255, 215, 75), font=font_badge)

    # Bottom Print/Edition Badge
    bw_b, bh_b = 104, 22
    bx_b = x + (w - bw_b) // 2
    by_b = y + h - bh_b - 1
    badge_poly_b = [
        (bx_b + 4, by_b),
        (bx_b + bw_b - 4, by_b),
        (bx_b + bw_b, by_b + bh_b - 8),
        (bx_b + bw_b - 8, by_b + bh_b),
        (bx_b + 8, by_b + bh_b),
        (bx_b, by_b + bh_b - 8)
    ]
    draw.polygon(badge_poly_b, fill=(18, 19, 22), outline=(75, 80, 90), width=1)

    m_bbox = font_badge.getbbox(mint_text)
    m_tw = m_bbox[2] - m_bbox[0] if m_bbox else len(mint_text) * 8
    m_th = m_bbox[3] - m_bbox[1] if m_bbox else 12
    draw.text((bx_b + (bw_b - m_tw) // 2, by_b + (bh_b - m_th) // 2),
              mint_text, fill=(255, 215, 75), font=font_badge)

# ==========================================
# 🃏 RENDER DROP CARDS (3 side-by-side)
# ==========================================
async def render_cards_image(cards: list, show_quality: bool = False) -> io.BytesIO:
    """Renders 3 authentic Karuta cards side-by-side for /drop."""
    card_w, card_h = 280, 450
    t_frame = 14
    banner_h = 100       # Increased vertical height of name & series banners to show less image
    gap = 20
    pad = 24

    canvas_w = (card_w * 3) + (gap * 2) + (pad * 2)
    canvas_h = card_h + (pad * 2)

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (14, 15, 18, 255))
    draw = ImageDraw.Draw(canvas)

    session = await get_http_session()
    medium_urls = [card["image"].replace("/large/", "/medium/") if card.get("image") else card.get("image") for card in cards]
    tasks = [fetch_image(session, url) for url in medium_urls]
    raw_images = await asyncio.gather(*tasks)

    banner_w = card_w - t_frame * 2
    top_banner_img = _create_gold_banner(banner_w, banner_h, arch_type="top")
    bot_banner_img = _create_gold_banner(banner_w, banner_h, arch_type="bottom")

    for i, card in enumerate(cards):
        cx = pad + i * (card_w + gap)
        cy = pad

        q_val = card.get("quality", "Good ⭐⭐")
        mint_str = f"{card['temp_mint']} · {card.get('edition', 1)}"

        # 1. Draw Full Rectangular Frame Base
        _draw_karuta_frame_structure(draw, cx, cy, card_w, card_h)

        # 2. Artwork Viewport
        content_x = cx + t_frame
        content_y = cy + t_frame
        content_w = card_w - t_frame * 2
        content_h = card_h - t_frame * 2

        fitted_art = fit_and_crop_image(raw_images[i], content_w, content_h)
        if show_quality:
            fitted_art = apply_quality_filter_to_image(fitted_art, q_val)

        canvas.paste(fitted_art, (content_x, content_y))

        if show_quality:
            apply_quality_effects_on_artwork(draw, content_x, content_y, content_w, content_h, q_val)

        # 3. Taller Gold Banners
        canvas.paste(top_banner_img, (content_x, content_y), top_banner_img)
        canvas.paste(bot_banner_img, (content_x, content_y + content_h - banner_h), bot_banner_img)

        # 4. Character Name (Top Banner — Prominent & Centered in Taller Banner)
        char_name = card["name"][:20]
        c_bbox = FONT_TITLE_DROP.getbbox(char_name)
        c_tw = c_bbox[2] - c_bbox[0] if c_bbox else len(char_name) * 15
        c_th = c_bbox[3] - c_bbox[1] if c_bbox else 26
        nx = content_x + (content_w - c_tw) // 2
        ny = content_y + (banner_h - 12 - c_th) // 2
        draw.text((nx + 1, ny + 1), char_name, fill=(240, 210, 110), font=FONT_TITLE_DROP)
        draw.text((nx, ny), char_name, fill=(35, 30, 20), font=FONT_TITLE_DROP)

        # 5. Series Name (Bottom Banner — Prominent & Centered in Taller Banner)
        series_name = card["series"][:22]
        s_bbox = FONT_SERIES_DROP.getbbox(series_name)
        s_tw = s_bbox[2] - s_bbox[0] if s_bbox else len(series_name) * 12
        s_th = s_bbox[3] - s_bbox[1] if s_bbox else 20
        sx = content_x + (content_w - s_tw) // 2
        sy = content_y + content_h - banner_h + (banner_h + 12 - s_th) // 2 - 4
        draw.text((sx + 1, sy + 1), series_name, fill=(240, 210, 110), font=FONT_SERIES_DROP)
        draw.text((sx, sy), series_name, fill=(35, 30, 20), font=FONT_SERIES_DROP)

        # 6. Badges
        _draw_karuta_badges(draw, cx, cy, card_w, card_h, card["code"], mint_str, FONT_BADGE_DROP)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ==========================================
# 🃏 RENDER SINGLE CARD (view/lookup)
# ==========================================
async def render_single_card(card_data: dict) -> io.BytesIO:
    """Renders a single authentic Karuta card for /card."""
    card_w, card_h = 320, 500
    t_frame = 16
    banner_h = 112       # Increased vertical height of name & series banners to show less image
    pad = 20

    canvas_w = card_w + pad * 2
    canvas_h = card_h + pad * 2

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (14, 15, 18, 0))
    draw = ImageDraw.Draw(canvas)

    session = await get_http_session()
    raw_img = await fetch_image(session, card_data["image_url"])

    q_val = card_data.get("quality", "Good ⭐⭐")
    mint_str = f"{card_data['mint_number']} · {card_data.get('edition', 1)}"

    cx, cy = pad, pad
    _draw_karuta_frame_structure(draw, cx, cy, card_w, card_h)

    content_x = cx + t_frame
    content_y = cy + t_frame
    content_w = card_w - t_frame * 2
    content_h = card_h - t_frame * 2

    fitted_art = fit_and_crop_image(raw_img, content_w, content_h)
    filtered_art = apply_quality_filter_to_image(fitted_art, q_val)
    canvas.paste(filtered_art, (content_x, content_y))
    apply_quality_effects_on_artwork(draw, content_x, content_y, content_w, content_h, q_val)

    top_banner_img = _create_gold_banner(content_w, banner_h, arch_type="top")
    bot_banner_img = _create_gold_banner(content_w, banner_h, arch_type="bottom")
    canvas.paste(top_banner_img, (content_x, content_y), top_banner_img)
    canvas.paste(bot_banner_img, (content_x, content_y + content_h - banner_h), bot_banner_img)

    char_name = card_data["character_name"][:22]
    c_bbox = FONT_TITLE_SINGLE.getbbox(char_name)
    c_tw = c_bbox[2] - c_bbox[0] if c_bbox else len(char_name) * 16
    c_th = c_bbox[3] - c_bbox[1] if c_bbox else 30
    nx = content_x + (content_w - c_tw) // 2
    ny = content_y + (banner_h - 14 - c_th) // 2
    draw.text((nx + 1, ny + 1), char_name, fill=(240, 210, 110), font=FONT_TITLE_SINGLE)
    draw.text((nx, ny), char_name, fill=(35, 30, 20), font=FONT_TITLE_SINGLE)

    series_name = card_data["series_name"][:24]
    s_bbox = FONT_SERIES_SINGLE.getbbox(series_name)
    s_tw = s_bbox[2] - s_bbox[0] if s_bbox else len(series_name) * 13
    s_th = s_bbox[3] - s_bbox[1] if s_bbox else 22
    sx = content_x + (content_w - s_tw) // 2
    sy = content_y + content_h - banner_h + (banner_h + 14 - s_th) // 2 - 4
    draw.text((sx + 1, sy + 1), series_name, fill=(240, 210, 110), font=FONT_SERIES_SINGLE)
    draw.text((sx, sy), series_name, fill=(35, 30, 20), font=FONT_SERIES_SINGLE)

    _draw_karuta_badges(draw, cx, cy, card_w, card_h, card_data["code"], mint_str, FONT_BADGE_SINGLE)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

render_three_cards_composite = render_cards_image
