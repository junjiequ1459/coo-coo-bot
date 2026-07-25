import io
import os
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 🔤 FONT LOADING
# ==========================================
def _load_font(size, display=False):
    """Load a scalable font while preserving the requested pixel size."""
    if display:
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
            "/System/Library/Fonts/SFNSRounded.ttf",
            "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
    else:
        font_paths = [
            "/System/Library/Fonts/Supplemental/Trebuchet MS Bold Italic.ttf",
            "/System/Library/Fonts/Avenir Next Condensed.ttc",
            "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
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
    return _load_font(size, display=True)

# Pre-load clean fonts at sizes that match the card proportions.
FONT_TITLE_DROP = _load_font(34, display=True)
FONT_SERIES_DROP = _load_font(18)
FONT_BADGE_DROP = _load_monospace_font(15)

FONT_TITLE_SINGLE = _load_font(40, display=True)
FONT_SERIES_SINGLE = _load_font(21)
FONT_BADGE_SINGLE = _load_monospace_font(17)


def _text_width(font, text: str) -> int:
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0] if bbox else 0


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    """Wrap text by measured pixel width, including words wider than one line."""
    words = " ".join(str(text).split()).split(" ")
    if not words or words == [""]:
        return [""]

    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and _text_width(font, candidate) <= max_width:
            current = candidate
            continue
        if not current and _text_width(font, word) <= max_width:
            current = word
            continue
        if current:
            lines.append(current)
            current = ""

        piece = ""
        for char in word:
            candidate_piece = piece + char
            if piece and _text_width(font, candidate_piece) > max_width:
                lines.append(piece)
                piece = char
            else:
                piece = candidate_piece
        current = piece

    if current:
        lines.append(current)
    return lines


def _prepare_wrapped_text(font, text: str, max_width: int, min_size: int, max_lines: int = 2):
    """Keep short text large and reduce only wrapped text enough to stay compact."""
    lines = _wrap_text(text, font, max_width)
    current_size = getattr(font, "size", min_size)

    if len(lines) > 1 and current_size > min_size:
        current_size = max(min_size, round(current_size * 0.8))
        try:
            font = font.font_variant(size=current_size)
            lines = _wrap_text(text, font, max_width)
        except (AttributeError, OSError):
            return font, lines

    while len(lines) > max_lines and current_size > min_size:
        current_size = max(min_size, current_size - 1)
        try:
            font = font.font_variant(size=current_size)
        except (AttributeError, OSError):
            break
        lines = _wrap_text(text, font, max_width)

    return font, lines


def _font_line_height(font) -> int:
    bbox = font.getbbox("Ag")
    return bbox[3] - bbox[1] if bbox else getattr(font, "size", 14)


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

def crop_artwork_to_card(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Center-crop artwork to the card ratio while preserving its proportions."""
    source_w, source_h = img.size
    if source_w <= 0 or source_h <= 0:
        return img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    source_ratio = source_w / source_h
    target_ratio = target_w / target_h

    if source_ratio > target_ratio:
        crop_w = max(1, round(source_h * target_ratio))
        left = (source_w - crop_w) // 2
        crop_box = (left, 0, left + crop_w, source_h)
    else:
        crop_h = max(1, round(source_w / target_ratio))
        top = (source_h - crop_h) // 2
        crop_box = (0, top, source_w, top + crop_h)

    cropped = img.crop(crop_box)
    return cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)

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

    # 2. Artwork Viewport (aspect-ratio crop; no stretching)
    fitted_art = crop_artwork_to_card(raw_img, content_w, content_h)

    # Rounded corners mask for inner content box
    art_mask = Image.new("L", (content_w, content_h), 0)
    art_mask_draw = ImageDraw.Draw(art_mask)
    art_mask_draw.rounded_rectangle([0, 0, content_w - 1, content_h - 1], radius=8, fill=255)

    canvas.paste(fitted_art, (content_x, content_y), art_mask)

    series_name = str(
        card_data.get("series")
        or card_data.get("series_name")
        or "Genshin Impact"
    )
    char_name = str(
        card_data.get("name")
        or card_data.get("character_name")
        or "Citlali"
    )

    font_series, series_lines = _prepare_wrapped_text(
        font_series,
        series_name,
        content_w - 36,
        min_size=11,
    )
    font_title, title_lines = _prepare_wrapped_text(
        font_title,
        char_name,
        content_w - 24,
        min_size=16,
    )

    series_line_h = _font_line_height(font_series)
    title_line_h = _font_line_height(font_title)
    series_spacing = 1
    title_spacing = 0
    series_block_h = (
        series_line_h * len(series_lines)
        + series_spacing * max(0, len(series_lines) - 1)
    )
    title_block_h = (
        title_line_h * len(title_lines)
        + title_spacing * max(0, len(title_lines) - 1)
    )

    card_code = str(card_data.get("code", "VL9BSJ3")).upper()
    mint_val = card_data.get("temp_mint", card_data.get("mint_number", 912))
    ed_val = card_data.get("edition", 2)
    edition_str = f"{mint_val} · {ed_val}"

    code_bbox = font_badge.getbbox(card_code)
    code_tw = code_bbox[2] - code_bbox[0] if code_bbox else len(card_code) * 7
    code_th = code_bbox[3] - code_bbox[1] if code_bbox else 12
    badge_pw = code_tw + 16
    badge_ph = code_th + 6

    ed_bbox = font_badge.getbbox(edition_str)
    ed_tw = ed_bbox[2] - ed_bbox[0] if ed_bbox else len(edition_str) * 7
    ed_th = ed_bbox[3] - ed_bbox[1] if ed_bbox else 12
    ed_pw = ed_tw + 16
    ed_ph = ed_th + 6

    # 3. Compact opaque overlay, expanding only when wrapped text needs it.
    base_panel_h = max(100, int(content_h * 0.24))
    required_panel_h = (
        7
        + series_block_h
        + 2
        + title_block_h
        + 5
        + max(badge_ph, ed_ph)
        + 10
    )
    bot_h = max(base_panel_h, required_panel_h)
    bot_y = content_y + content_h - bot_h

    bot_overlay = Image.new("RGBA", (content_w, bot_h), (0, 0, 0, 0))
    bo_draw = ImageDraw.Draw(bot_overlay)

    panel_top = (251, 237, 190)
    panel_bottom = (232, 198, 116)
    for panel_y in range(bot_h):
        blend = panel_y / max(1, bot_h - 1)
        panel_color = tuple(
            int(start + ((end - start) * blend))
            for start, end in zip(panel_top, panel_bottom)
        )
        bo_draw.line(
            [(0, panel_y), (content_w - 1, panel_y)],
            fill=panel_color + (255,),
        )
    bo_draw.line([(0, 0), (content_w - 1, 0)], fill=(104, 83, 43, 225), width=2)

    canvas.paste(bot_overlay, (content_x, bot_y), bot_overlay)

    # 4. Wrapped series and character names, centered in the space above badges
    text_group_h = series_block_h + 2 + title_block_h
    badge_row_top = content_y + content_h - max(badge_ph, ed_ph) - 4
    text_area_top = bot_y + 4
    text_area_bottom = badge_row_top - 5
    text_area_h = max(text_group_h, text_area_bottom - text_area_top)
    sy = text_area_top + max(0, (text_area_h - text_group_h) // 2)
    series_max_w = max(_text_width(font_series, line) for line in series_lines)
    line_y = sy + series_block_h // 2
    margin = 14
    left_line_x1 = content_x + margin
    left_line_x2 = content_x + (content_w - series_max_w) // 2 - 8
    right_line_x1 = content_x + (content_w + series_max_w) // 2 + 8
    right_line_x2 = content_x + content_w - margin

    line_segments = (
        (left_line_x1, left_line_x2),
        (right_line_x1, right_line_x2),
    )
    if "mythic" in rarity_str:
        for line_x1, line_x2 in line_segments:
            if line_x2 > line_x1:
                _draw_rainbow_line(canvas, (line_x1, line_y, line_x2, line_y + 2))
    else:
        line_color = (
            (255, 193, 59, 230)
            if "legend" in rarity_str
            else (167, 116, 255, 230)
            if "epic" in rarity_str
            else (44, 207, 255, 230)
            if "rare" in rarity_str
            else (143, 157, 176, 220)
        )
        for line_x1, line_x2 in line_segments:
            if line_x2 > line_x1:
                draw.line([(line_x1, line_y), (line_x2, line_y)], fill=line_color, width=2)

    center_x = content_x + content_w // 2
    for line_index, line in enumerate(series_lines):
        draw.text(
            (center_x, sy + line_index * (series_line_h + series_spacing)),
            line,
            fill=(58, 50, 34),
            font=font_series,
            anchor="mt",
        )

    title_y = sy + series_block_h + 2
    for line_index, line in enumerate(title_lines):
        draw.text(
            (center_x, title_y + line_index * (title_line_h + title_spacing)),
            line,
            fill=(24, 25, 27),
            font=font_title,
            anchor="mt",
            stroke_width=1,
            stroke_fill=(255, 242, 196, 210),
        )

    # 5. Bottom Row: Left Pill Code Badge & Right Print/Edition Text
    badge_px = content_x + 12
    badge_py = content_y + content_h - badge_ph - 4

    code_pill = Image.new("RGBA", (badge_pw, badge_ph), (0, 0, 0, 0))
    cp_draw = ImageDraw.Draw(code_pill)
    code_cut = min(5, badge_ph // 3)
    code_shape = [
        (code_cut, 0),
        (badge_pw - code_cut - 1, 0),
        (badge_pw - 1, code_cut),
        (badge_pw - 1, badge_ph - code_cut - 1),
        (badge_pw - code_cut - 1, badge_ph - 1),
        (code_cut, badge_ph - 1),
        (0, badge_ph - code_cut - 1),
        (0, code_cut),
    ]
    cp_draw.polygon(code_shape, fill=(18, 19, 22, 255))
    cp_draw.line(code_shape + [code_shape[0]], fill=(93, 75, 40), width=1)
    cp_draw.text(
        (badge_pw // 2, badge_ph // 2),
        card_code,
        fill=(245, 205, 91),
        font=font_badge,
        anchor="mm",
    )
    canvas.paste(code_pill, (badge_px, badge_py), code_pill)

    ed_px = content_x + content_w - ed_pw - 12
    ed_py = content_y + content_h - ed_ph - 4

    ed_pill = Image.new("RGBA", (ed_pw, ed_ph), (0, 0, 0, 0))
    ep_draw = ImageDraw.Draw(ed_pill)
    ed_cut = min(5, ed_ph // 3)
    ed_shape = [
        (ed_cut, 0),
        (ed_pw - ed_cut - 1, 0),
        (ed_pw - 1, ed_cut),
        (ed_pw - 1, ed_ph - ed_cut - 1),
        (ed_pw - ed_cut - 1, ed_ph - 1),
        (ed_cut, ed_ph - 1),
        (0, ed_ph - ed_cut - 1),
        (0, ed_cut),
    ]
    ep_draw.polygon(ed_shape, fill=(18, 19, 22, 255))
    ep_draw.line(ed_shape + [ed_shape[0]], fill=(93, 75, 40), width=1)
    ep_draw.text(
        (ed_pw // 2, ed_ph // 2),
        edition_str,
        fill=(245, 205, 91),
        font=font_badge,
        anchor="mm",
    )
    canvas.paste(ed_pill, (ed_px, ed_py), ed_pill)

# ==========================================
# 🃏 RENDER DROP CARDS (3 side-by-side)
# ==========================================
async def render_three_cards_composite(cards: list) -> io.BytesIO:
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
