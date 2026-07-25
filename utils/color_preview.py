import os
from PIL import Image, ImageDraw, ImageFont

def generate_color_preview(output_path="color_preview.png"):
    width, height = 900, 280
    # Create dark background matching Discord dark mode
    img = Image.new("RGBA", (width, height), (30, 31, 34, 255))
    draw = ImageDraw.Draw(img)

    # Card background panel
    panel_margin = 15
    draw.rounded_rectangle(
        [panel_margin, panel_margin, width - panel_margin, height - panel_margin],
        radius=20,
        fill=(43, 45, 49, 255),
        outline=(58, 60, 65, 255),
        width=2
    )

    colors = [
        {"name": "Ratan", "desc": "Yellow", "rgb": (255, 250, 205), "hex": "#FFFACD"},
        {"name": "Miin", "desc": "Pink", "rgb": (255, 182, 193), "hex": "#FFB6C1"},
        {"name": "Coo Coo", "desc": "Light Blue", "rgb": (135, 206, 235), "hex": "#87CEEB"},
    ]

    card_width = (width - 80) // 3
    
    # Try loading a system font or default font
    font_large = None
    font_small = None
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    for i, col in enumerate(colors):
        x_start = 40 + i * (card_width + 10)
        y_start = 35
        card_h = height - 70

        # Swatch container card
        draw.rounded_rectangle(
            [x_start, y_start, x_start + card_width, y_start + card_h],
            radius=16,
            fill=(35, 36, 40, 255),
            outline=(60, 63, 68, 255),
            width=1
        )

        # Color Circle Swatch
        circle_size = 80
        cx = x_start + (card_width - circle_size) // 2
        cy = y_start + 25

        # Inner shadow / subtle glow around circle
        draw.ellipse([cx - 3, cy - 3, cx + circle_size + 3, cy + circle_size + 3], fill=(col["rgb"][0]//2, col["rgb"][1]//2, col["rgb"][2]//2, 100))
        draw.ellipse([cx, cy, cx + circle_size, cy + circle_size], fill=col["rgb"] + (255,))

        # Text labels
        # Name
        bbox = font_large.getbbox(col["name"])
        tw = bbox[2] - bbox[0]
        tx = x_start + (card_width - tw) // 2
        ty = cy + circle_size + 20
        draw.text((tx, ty), col["name"], fill=(240, 240, 245), font=font_large)

        # Color Desc & Hex
        sub_text = f"{col['desc']} ({col['hex']})"
        s_bbox = font_small.getbbox(sub_text)
        stw = s_bbox[2] - s_bbox[0]
        stx = x_start + (card_width - stw) // 2
        sty = ty + 36
        draw.text((stx, sty), sub_text, fill=(160, 165, 175), font=font_small)

    img.save(output_path)
    print(f"Color preview saved to {output_path}")

if __name__ == "__main__":
    generate_color_preview()
