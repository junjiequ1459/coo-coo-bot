import os

from PIL import ImageFont


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
