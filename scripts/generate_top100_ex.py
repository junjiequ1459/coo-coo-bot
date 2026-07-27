import urllib.request
import urllib.parse
import re
import json
import psycopg2
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_connection, release_connection

def get_top_100():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT character_name, series_name, favourites 
        FROM cards_pool 
        WHERE rarity != 'Exalted' 
          AND character_name NOT LIKE '% EX'
          AND character_name NOT IN (
              SELECT REPLACE(character_name, ' EX', '') 
              FROM cards_pool 
              WHERE rarity = 'Exalted'
          )
        ORDER BY favourites DESC 
        LIMIT 100
    """)
    rows = cur.fetchall()
    release_connection(conn)
    return rows

def fetch_gif_url(char_name, series_name):
    query = f"{char_name} {series_name} gif"
    url = "https://tenor.com/search/" + urllib.parse.quote(query.replace(" ", "-"))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        html = urllib.request.urlopen(req).read().decode("utf-8")
        links = re.findall(r"https://media1\.tenor\.com/m/[^\"]+\.gif", html)
        if links:
            return links[0]
        return None
    except Exception as e:
        print(f"Error fetching {query}: {e}")
        return None

if __name__ == "__main__":
    print("Fetching top 100 characters...")
    chars = get_top_100()
    results = []
    
    print(f"Found {len(chars)} characters. Scraping GIFs...")
    for i, (name, series, favs) in enumerate(chars):
        print(f"[{i+1}/100] Scraping {name}...")
        gif_url = fetch_gif_url(name, series)
        results.append({
            "character_name": f"{name} EX",
            "series_name": series,
            "image_url": gif_url or "https://via.placeholder.com/280x450.gif?text=Not+Found",
            "rarity": "Exalted",
            "favourites": favs
        })
        time.sleep(0.5)
        
    with open("scripts/preview_exalted.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print("Saved preview to scripts/preview_exalted.json")
