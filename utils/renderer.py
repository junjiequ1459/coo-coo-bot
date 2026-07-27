import asyncio
import io

from PIL import Image

from utils.rendering.artwork import fetch_image, get_http_session
from utils.rendering.card import draw_card_on_canvas
from utils.rendering.fonts import (
    FONT_BADGE_DROP, FONT_BADGE_SINGLE, FONT_SERIES_DROP,
    FONT_SERIES_SINGLE, FONT_TITLE_DROP, FONT_TITLE_SINGLE,
)


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
async def render_single_card(card_data: dict) -> tuple[io.BytesIO, bool]:
    """Renders a single card for /card. Returns (buffer, is_gif)"""
    card_w, card_h = 320, 500
    pad = 20

    canvas_w = card_w + pad * 2
    canvas_h = card_h + pad * 2

    session = await get_http_session()
    raw_img = await fetch_image(session, card_data["image_url"])

    rarity_str = str(card_data.get("rarity", "Legendary")).lower()
    is_gif = getattr(raw_img, "is_animated", False)

    if rarity_str == "exalted" and not is_gif:
        is_gif = True
        frames_source = [raw_img] * 30
        durations = 40
    elif is_gif:
        from PIL import ImageSequence
        frames_source = [f.copy() for f in ImageSequence.Iterator(raw_img)]
        durations = raw_img.info.get('duration', 100)
    else:
        frames_source = None

    if is_gif:
        frames = []
        total_frames = len(frames_source)
        for i, frame in enumerate(frames_source):
            frame = frame.convert("RGBA")
            canvas = Image.new("RGBA", (canvas_w, canvas_h), (14, 15, 18, 0))
            hue = (i / total_frames) if rarity_str == "exalted" else 0.0
            
            draw_card_on_canvas(canvas, pad, pad, card_w, card_h, frame, card_data,
                                FONT_TITLE_SINGLE, FONT_SERIES_SINGLE, FONT_BADGE_SINGLE, hue)
            frames.append(canvas)
            
        buf = io.BytesIO()
        frames[0].save(
            buf, 
            format="GIF", 
            save_all=True, 
            append_images=frames[1:], 
            duration=durations, 
            loop=0,
            disposal=2,
            optimize=True
        )
        buf.seek(0)
        return buf, True
    else:
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (14, 15, 18, 0))
        draw_card_on_canvas(canvas, pad, pad, card_w, card_h, raw_img, card_data,
                            FONT_TITLE_SINGLE, FONT_SERIES_SINGLE, FONT_BADGE_SINGLE)
        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        buf.seek(0)
        return buf, False
