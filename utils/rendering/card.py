from PIL import Image, ImageDraw

from utils.rendering.artwork import crop_artwork_to_card
from utils.rendering.decorations import draw_badge, draw_rarity_gem
from utils.rendering.fonts import (
    _font_line_height, _prepare_wrapped_text,
)
from utils.rendering.frame import create_metal_frame, create_exalted_frame
from utils.rendering.panel import create_information_panel

# ==========================================
# 🖼️ DRAW CARD (Silver Metallic Border Design)
# ==========================================
def draw_card_on_canvas(canvas: Image.Image, x: int, y: int, card_w: int, card_h: int,
                        raw_img: Image.Image, card_data: dict, font_title, font_series, font_badge, hue: float = 0.0):
    """Draws a card with a sleek 3D silver-gray metallic outer border matching the user's mockup."""
    draw = ImageDraw.Draw(canvas)
    rarity_str = str(card_data.get("rarity", "Legendary")).lower()

    if rarity_str == "exalted":
        frame_img, view_x, view_y, view_w, view_h = create_exalted_frame(
            card_w,
            card_h,
            hue,
        )
    else:
        frame_img, view_x, view_y, view_w, view_h = create_metal_frame(
            card_w,
            card_h,
        )
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

    # Keep the left card-code badge and right edition badge identical in size.
    badge_pw = ed_pw = max(badge_pw, ed_pw)
    badge_ph = ed_ph = max(badge_ph, ed_ph)

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

    bot_overlay = create_information_panel(content_w, bot_h)
    canvas.paste(bot_overlay, (content_x, bot_y), bot_overlay)

    # 4. Wrapped series and character names, centered in the space above badges
    text_group_h = series_block_h + 2 + title_block_h
    badge_row_top = content_y + content_h - max(badge_ph, ed_ph) - 4
    text_area_top = bot_y + 4
    text_area_bottom = badge_row_top - 5
    text_area_h = max(text_group_h, text_area_bottom - text_area_top)
    sy = text_area_top + max(0, (text_area_h - text_group_h) // 2)
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

    draw_badge(
        canvas,
        (badge_px, badge_py),
        (badge_pw, badge_ph),
        card_code,
        font_badge,
    )

    ed_px = content_x + content_w - ed_pw - 12
    ed_py = content_y + content_h - ed_ph - 4

    draw_badge(
        canvas,
        (ed_px, ed_py),
        (ed_pw, ed_ph),
        edition_str,
        font_badge,
    )

    # Centered rarity gem between the card ID and print/edition badges.
    gem_half_w = max(7, round(card_w * 0.027))
    gem_half_h = max(8, round(card_h * 0.019))
    gem_center_y = badge_row_top + max(badge_ph, ed_ph) // 2
    draw_rarity_gem(
        draw,
        rarity_str,
        (center_x, gem_center_y),
        gem_half_w,
        gem_half_h,
    )
