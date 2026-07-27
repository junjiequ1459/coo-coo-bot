import colorsys
from PIL import Image, ImageChops, ImageDraw, ImageFilter


def create_metal_frame(
    card_width: int,
    card_height: int,
) -> tuple[Image.Image, int, int, int, int]:
    """Create the silver frame and return its inner content bounds."""
    frame_width = max(18, round(card_width * 0.06))
    frame_radius = max(20, round(card_width * 0.075))
    frame = Image.new(
        "RGBA",
        (card_width, card_height),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(frame)

    draw.rounded_rectangle(
        [0, 0, card_width - 1, card_height - 1],
        radius=frame_radius,
        fill=(174, 180, 190),
        outline=(224, 228, 235),
        width=2,
    )
    draw.rounded_rectangle(
        [6, 6, card_width - 7, card_height - 7],
        radius=frame_radius - 6,
        fill=(116, 122, 132),
        outline=(92, 97, 106),
        width=2,
    )
    draw.rounded_rectangle(
        [10, 10, card_width - 11, card_height - 11],
        radius=frame_radius - 10,
        fill=(150, 156, 166),
        outline=(202, 207, 216),
        width=2,
    )

    view_x = view_y = frame_width
    view_width = card_width - frame_width * 2
    view_height = card_height - frame_width * 2

    draw.rounded_rectangle(
        [
            view_x - 3,
            view_y - 3,
            view_x + view_width + 2,
            view_y + view_height + 2,
        ],
        radius=11,
        fill=(150, 156, 166),
        outline=(202, 207, 216),
        width=2,
    )
    draw.rounded_rectangle(
        [
            view_x,
            view_y,
            view_x + view_width - 1,
            view_y + view_height - 1,
        ],
        radius=8,
        fill=(116, 122, 132),
        outline=(150, 156, 166),
        width=1,
    )

    frame_mask = Image.new("L", (card_width, card_height), 0)
    mask_draw = ImageDraw.Draw(frame_mask)
    mask_draw.rounded_rectangle(
        [0, 0, card_width - 1, card_height - 1],
        radius=frame_radius,
        fill=255,
    )
    mask_draw.rounded_rectangle(
        [
            view_x - 1,
            view_y - 1,
            view_x + view_width,
            view_y + view_height,
        ],
        radius=9,
        fill=0,
    )

    light_layer = Image.new(
        "RGBA",
        (card_width, card_height),
        (0, 0, 0, 0),
    )
    light_draw = ImageDraw.Draw(light_layer)
    light_draw.ellipse(
        [
            -card_width // 2,
            -card_height // 3,
            round(card_width * 0.9),
            round(card_height * 0.72),
        ],
        fill=(255, 255, 255, 105),
    )
    light_layer = light_layer.filter(
        ImageFilter.GaussianBlur(max(8, frame_width))
    )
    light_layer.putalpha(
        ImageChops.multiply(light_layer.getchannel("A"), frame_mask)
    )
    frame = Image.alpha_composite(frame, light_layer)

    shade_layer = Image.new(
        "RGBA",
        (card_width, card_height),
        (0, 0, 0, 0),
    )
    shade_draw = ImageDraw.Draw(shade_layer)
    shade_draw.ellipse(
        [
            round(card_width * 0.28),
            round(card_height * 0.38),
            round(card_width * 1.45),
            round(card_height * 1.38),
        ],
        fill=(42, 47, 58, 55),
    )
    shade_layer = shade_layer.filter(
        ImageFilter.GaussianBlur(max(8, frame_width))
    )
    shade_layer.putalpha(
        ImageChops.multiply(shade_layer.getchannel("A"), frame_mask)
    )
    frame = Image.alpha_composite(frame, shade_layer)

    lit_draw = ImageDraw.Draw(frame)
    lit_draw.line(
        [(frame_radius, 2), (card_width - frame_radius, 2)],
        fill=(248, 250, 253, 210),
        width=1,
    )
    lit_draw.line(
        [(2, frame_radius), (2, card_height - frame_radius)],
        fill=(248, 250, 253, 185),
        width=1,
    )
    lit_draw.line(
        [
            (frame_radius, card_height - 3),
            (card_width - frame_radius, card_height - 3),
        ],
        fill=(83, 89, 100, 170),
        width=1,
    )
    lit_draw.line(
        [
            (card_width - 3, frame_radius),
            (card_width - 3, card_height - frame_radius),
        ],
        fill=(83, 89, 100, 150),
        width=1,
    )

    return frame, view_x, view_y, view_width, view_height


def create_exalted_frame(
    card_width: int,
    card_height: int,
    hue: float = 0.0,
) -> tuple[Image.Image, int, int, int, int]:
    """Create the dark Exalted frame with an animated rainbow inner border."""
    frame_width = max(18, round(card_width * 0.06))
    frame_radius = max(20, round(card_width * 0.075))
    frame = Image.new(
        "RGBA",
        (card_width, card_height),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(frame)

    # 1. Base dark layers (static)
    draw.rounded_rectangle(
        [0, 0, card_width - 1, card_height - 1],
        radius=frame_radius,
        fill=(32, 35, 41),
        outline=(0, 0, 0, 0),
        width=0,
    )
    draw.rounded_rectangle(
        [6, 6, card_width - 7, card_height - 7],
        radius=frame_radius - 6,
        fill=(20, 22, 26),
        outline=(0, 0, 0, 0),
        width=0,
    )
    draw.rounded_rectangle(
        [10, 10, card_width - 11, card_height - 11],
        radius=frame_radius - 10,
        fill=(28, 30, 36),
        outline=(0, 0, 0, 0),
        width=0,
    )

    view_x = view_y = frame_width
    view_width = card_width - frame_width * 2
    view_height = card_height - frame_width * 2

    # Inner border base
    draw.rounded_rectangle(
        [
            view_x - 3,
            view_y - 3,
            view_x + view_width + 2,
            view_y + view_height + 2,
        ],
        radius=11,
        fill=(28, 30, 36),
        outline=(0, 0, 0, 0),
        width=0,
    )

    draw.rounded_rectangle(
        [
            view_x,
            view_y,
            view_x + view_width - 1,
            view_y + view_height - 1,
        ],
        radius=8,
        fill=(14, 15, 18),
        outline=(0, 0, 0, 0),
        width=0,
    )

    # 2. Moving Rainbow Gradient
    rainbow_1d = Image.new("RGBA", (256, 1))
    pixels = []
    for i in range(256):
        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(i / 256.0, 0.65, 0.9)] 
        pixels.append((r, g, b, 255))
    rainbow_1d.putdata(pixels)
    
    tex_w, tex_h = int(card_width * 2.5), int(card_height * 2.5)
    rainbow_tex = rainbow_1d.resize((tex_w, tex_h)).rotate(45, expand=True)
    
    slide_dist = card_width
    x_offset = int(hue * slide_dist)
    y_offset = int(hue * slide_dist)
    
    rainbow_crop = rainbow_tex.crop((x_offset, y_offset, x_offset + card_width, y_offset + card_height))
    
    # 3. Mask for the strokes
    border_mask = Image.new("L", (card_width, card_height), 0)
    mask_draw = ImageDraw.Draw(border_mask)
    
    mask_draw.rounded_rectangle(
        [0, 0, card_width - 1, card_height - 1],
        radius=frame_radius,
        fill=0,
        outline=255,
        width=4,
    )
    mask_draw.rounded_rectangle(
        [6, 6, card_width - 7, card_height - 7],
        radius=frame_radius - 6,
        fill=0,
        outline=200,
        width=2,
    )
    mask_draw.rounded_rectangle(
        [view_x - 3, view_y - 3, view_x + view_width + 2, view_y + view_height + 2],
        radius=11,
        fill=0,
        outline=200,
        width=2,
    )
    mask_draw.rounded_rectangle(
        [view_x, view_y, view_x + view_width - 1, view_y + view_height - 1],
        radius=8,
        fill=0,
        outline=255,
        width=3,
    )

    rainbow_crop.putalpha(border_mask)
    frame.alpha_composite(rainbow_crop)

    frame_mask = Image.new("L", (card_width, card_height), 0)
    mask_draw = ImageDraw.Draw(frame_mask)
    mask_draw.rounded_rectangle(
        [0, 0, card_width - 1, card_height - 1],
        radius=frame_radius,
        fill=255,
    )
    mask_draw.rounded_rectangle(
        [
            view_x - 1,
            view_y - 1,
            view_x + view_width,
            view_y + view_height,
        ],
        radius=9,
        fill=0,
    )

    # Glowing light layer (slight tint of the rainbow color)
    light_layer = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    light_draw = ImageDraw.Draw(light_layer)
    light_draw.ellipse(
        [
            -card_width // 2,
            -card_height // 3,
            round(card_width * 0.9),
            round(card_height * 0.72),
        ],
        fill=(r, g, b, 40), # Subtle rainbow glow
    )
    light_layer = light_layer.filter(ImageFilter.GaussianBlur(max(8, frame_width)))
    light_layer.putalpha(ImageChops.multiply(light_layer.getchannel("A"), frame_mask))
    frame = Image.alpha_composite(frame, light_layer)

    # Shadows
    shade_layer = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade_layer)
    shade_draw.ellipse(
        [
            round(card_width * 0.28),
            round(card_height * 0.38),
            round(card_width * 1.45),
            round(card_height * 1.38),
        ],
        fill=(10, 11, 14, 120),
    )
    shade_layer = shade_layer.filter(ImageFilter.GaussianBlur(max(8, frame_width)))
    shade_layer.putalpha(ImageChops.multiply(shade_layer.getchannel("A"), frame_mask))
    frame = Image.alpha_composite(frame, shade_layer)

    # Edge highlights
    lit_draw = ImageDraw.Draw(frame)
    lit_draw.line(
        [(frame_radius, 2), (card_width - frame_radius, 2)],
        fill=(r, g, b, 180),
        width=1,
    )
    lit_draw.line(
        [(2, frame_radius), (2, card_height - frame_radius)],
        fill=(r, g, b, 150),
        width=1,
    )

    return frame, view_x, view_y, view_width, view_height
