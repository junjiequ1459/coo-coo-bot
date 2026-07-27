import io

import aiohttp
from PIL import Image, ImageDraw


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
                    return Image.open(io.BytesIO(data))
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
