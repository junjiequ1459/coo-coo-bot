import random
import asyncio
import aiohttp
from database import generate_card_code, get_next_mint, roll_card_quality

ANILIST_URL = "https://graphql.anilist.co"

ANILIST_QUERY = """query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    characters(sort: FAVOURITES_DESC) {
      id
      name {
        full
      }
      image {
        large
      }
      favourites
      media(perPage: 1) {
        nodes {
          title {
            english
            romaji
          }
        }
      }
    }
  }
}"""

async def fetch_single_card_from_page(session, page: int):
    variables = {"page": page, "perPage": 25}
    try:
        async with session.post(ANILIST_URL, json={"query": ANILIST_QUERY, "variables": variables}, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                char_list = data["data"]["Page"]["characters"]
                if char_list:
                    return random.choice(char_list)
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
    return None

async def fetch_random_anilist_cards(count: int = 3):
    """Fetches 3 individual random characters from varied AniList popularity tiers."""
    pages_to_sample = [
        random.randint(1, 4),    # Top Tier / Legendary / Epic candidates
        random.randint(5, 18),   # Mid Tier / Epic / Rare candidates
        random.randint(19, 50)   # Lower Tier / Rare / Common candidates
    ]
    random.shuffle(pages_to_sample)
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_single_card_from_page(session, p) for p in pages_to_sample[:count]]
        results = await asyncio.gather(*tasks)

    cards = []
    for char in results:
        if not char:
            continue
        char_name = char["name"]["full"]
        img_url = char["image"]["large"]
        favs = char.get("favourites", 0)
        
        media_nodes = char.get("media", {}).get("nodes", [])
        if media_nodes and media_nodes[0].get("title"):
            series = media_nodes[0]["title"].get("english") or media_nodes[0]["title"].get("romaji") or "Anime Series"
        else:
            series = "Anime Series"
            
        if favs >= 12000:
            rarity = "✨ Legendary"
        elif favs >= 4000:
            rarity = "🟣 Epic"
        elif favs >= 1000:
            rarity = "🔷 Rare"
        else:
            rarity = "⚪ Common"
            
        temp_mint = get_next_mint(char_name)
        cards.append({
            "code": generate_card_code(),
            "name": char_name,
            "series": series,
            "image": img_url,
            "rarity": rarity,
            "quality": roll_card_quality(),
            "temp_mint": temp_mint,
            "edition": 1
        })

    DEFAULT_FALLBACKS = [
        {"name": "Satoru Gojo", "series": "Jujutsu Kaisen", "image": "https://s4.anilist.co/file/anilistcdn/character/large/b126448-aN2d0hG0240d.png", "rarity": "✨ Legendary"},
        {"name": "Monkey D. Luffy", "series": "One Piece", "image": "https://s4.anilist.co/file/anilistcdn/character/large/b40-X1W0z9Wn99g5.png", "rarity": "✨ Legendary"},
        {"name": "Naruto Uzumaki", "series": "Naruto", "image": "https://s4.anilist.co/file/anilistcdn/character/large/b17-0Vp9jR65iX1X.png", "rarity": "✨ Legendary"}
    ]

    idx = 0
    while len(cards) < count:
        fb = DEFAULT_FALLBACKS[idx % len(DEFAULT_FALLBACKS)]
        temp_mint = get_next_mint(fb["name"])
        cards.append({
            "code": generate_card_code(),
            "name": fb["name"],
            "series": fb["series"],
            "image": fb["image"],
            "rarity": fb["rarity"],
            "quality": roll_card_quality(),
            "temp_mint": temp_mint,
            "edition": 1
        })
        idx += 1

    return cards
