import math

from PIL import Image, ImageDraw


def draw_badge(
    canvas: Image.Image,
    position: tuple[int, int],
    size: tuple[int, int],
    text: str,
    font,
) -> None:
    """Draw a centered label in the clipped black card badge."""
    width, height = size
    badge = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    cut = min(5, height // 3)
    shape = [
        (cut, 0),
        (width - cut - 1, 0),
        (width - 1, cut),
        (width - 1, height - cut - 1),
        (width - cut - 1, height - 1),
        (cut, height - 1),
        (0, height - cut - 1),
        (0, cut),
    ]
    draw.polygon(shape, fill=(18, 19, 22, 255))
    draw.line(shape + [shape[0]], fill=(93, 75, 40), width=1)
    draw.text(
        (width // 2, height // 2),
        text,
        fill=(245, 205, 91),
        font=font,
        anchor="mm",
    )
    canvas.paste(badge, position, badge)


def _rarity_gem_color(rarity: str) -> tuple[int, int, int]:
    colors = {
        "common": (174, 180, 190),
        "rare": (44, 170, 255),
        "epic": (167, 116, 255),
        "legendary": (255, 193, 59),
    }
    return colors.get(str(rarity).strip().lower(), colors["common"])


def draw_rarity_gem(
    draw: ImageDraw.ImageDraw,
    rarity: str,
    center: tuple[int, int],
    half_width: int,
    half_height: int,
) -> None:
    """Draw a faceted rarity gem or rainbow mythic star."""
    center_x, center_y = center
    gem_points = [
        (center_x, center_y - half_height),
        (center_x + half_width, center_y - half_height // 3),
        (center_x + half_width, center_y + half_height // 3),
        (center_x, center_y + half_height),
        (center_x - half_width, center_y + half_height // 3),
        (center_x - half_width, center_y - half_height // 3),
    ]

    if "mythic" in rarity:
        rainbow_facets = [
            (255, 74, 86),
            (255, 157, 48),
            (255, 220, 64),
            (62, 210, 112),
            (45, 170, 255),
            (176, 93, 255),
        ]
        star_radius = max(half_width, half_height)
        star_scale_x = star_radius / math.cos(math.pi / 6)
        star_points = []
        for index in range(12):
            angle = (-math.pi / 2) + (index * math.pi / 6)
            radius = 1 if index % 2 == 0 else 0.45
            star_points.append(
                (
                    round(center_x + math.cos(angle) * star_scale_x * radius),
                    round(center_y + math.sin(angle) * star_radius * radius),
                )
            )

        for index in range(12):
            draw.polygon(
                [
                    center,
                    star_points[index],
                    star_points[(index + 1) % len(star_points)],
                ],
                fill=rainbow_facets[(index // 2) % len(rainbow_facets)],
            )
        draw.line(
            star_points + [star_points[0]],
            fill=(18, 18, 18),
            width=1,
        )
        return

    gem_color = _rarity_gem_color(rarity)
    gem_highlight = tuple(
        min(255, channel + 70)
        for channel in gem_color
    )
    gem_shadow = tuple(
        max(0, round(channel * 0.55))
        for channel in gem_color
    )
    draw.polygon(gem_points, fill=gem_color)
    draw.polygon(
        [
            gem_points[0],
            gem_points[1],
            center,
            gem_points[5],
        ],
        fill=gem_highlight,
    )
    draw.polygon(
        [
            center,
            gem_points[2],
            gem_points[3],
            gem_points[4],
        ],
        fill=gem_shadow,
    )
    draw.line(
        gem_points + [gem_points[0]],
        fill=(18, 18, 18),
        width=1,
    )
