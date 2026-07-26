from PIL import Image, ImageDraw, ImageFilter


def create_information_panel(width: int, height: int) -> Image.Image:
    """Create the opaque gold information panel and its lighting."""
    panel = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)

    panel_top = (251, 237, 190)
    panel_bottom = (232, 198, 116)
    for y in range(height):
        blend = y / max(1, height - 1)
        panel_color = tuple(
            int(start + ((end - start) * blend))
            for start, end in zip(panel_top, panel_bottom)
        )
        draw.line(
            [(0, y), (width - 1, y)],
            fill=panel_color + (255,),
        )

    light = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    light_draw = ImageDraw.Draw(light)
    light_draw.ellipse(
        [
            -width // 2,
            -height,
            round(width * 0.9),
            round(height * 1.2),
        ],
        fill=(255, 255, 245, 75),
    )
    light = light.filter(
        ImageFilter.GaussianBlur(max(6, height // 8))
    )
    panel = Image.alpha_composite(panel, light)

    shade = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade)
    shade_draw.ellipse(
        [
            round(width * 0.35),
            round(height * 0.15),
            round(width * 1.45),
            round(height * 1.65),
        ],
        fill=(115, 75, 20, 42),
    )
    shade = shade.filter(
        ImageFilter.GaussianBlur(max(6, height // 8))
    )
    panel = Image.alpha_composite(panel, shade)

    draw = ImageDraw.Draw(panel)
    draw.line(
        [(0, 0), (width - 1, 0)],
        fill=(104, 83, 43, 225),
        width=2,
    )
    return panel
