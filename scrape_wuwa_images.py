import requests
from bs4 import BeautifulSoup
from db import get_connection, release_connection
import sys

import sys

HTML_PATH = "/Users/user/.gemini/antigravity/brain/f9c7a433-a520-42d6-aa70-9e8d362dafca/.system_generated/steps/135/content.md"

def run():
    print("Reading local Fandom Wiki HTML...")
    try:
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            html_text = f.read()
    except Exception as e:
        print(f"Failed to read file: {e}")
        sys.exit(1)

    soup = BeautifulSoup(html_text, "html.parser")
    gallery_items = soup.find_all("div", class_="wikia-gallery-item")
    
    updates = {}
    for item in gallery_items:
        caption_div = item.find("div", class_="lightbox-caption")
        if not caption_div:
            continue
            
        a_tag = caption_div.find("a")
        if not a_tag:
            continue
            
        char_name = a_tag.get_text(strip=True)
        
        img_tag = item.find("img", class_="thumbimage")
        if not img_tag:
            continue
            
        img_url = img_tag.get("data-src") or img_tag.get("src")
        if not img_url:
            continue
            
        if "Splash_Art" in img_url or "Splash Art" in img_url:
            # Clean up the URL to get the full resolution image
            clean_url = img_url.split(".png")[0] + ".png"
            updates[char_name] = clean_url

    print(f"Found {len(updates)} splash arts.")
    for name, url in list(updates.items())[:3]:
        print(f" - {name}: {url}")
        
    if not updates:
        print("No splash arts found. Exiting.")
        sys.exit(1)

    print("Connecting to database...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Update cards_pool
            pool_updated = 0
            for char_name, url in updates.items():
                cur.execute(
                    "UPDATE cards_pool SET image_url = %s WHERE series_name ILIKE %s AND character_name ILIKE %s",
                    (url, '%Wuthering Waves%', f"%{char_name}%")
                )
                pool_updated += cur.rowcount
            
            # Update inventory
            inv_updated = 0
            for char_name, url in updates.items():
                cur.execute(
                    "UPDATE inventory SET image_url = %s WHERE series_name ILIKE %s AND character_name ILIKE %s",
                    (url, '%Wuthering Waves%', f"%{char_name}%")
                )
                inv_updated += cur.rowcount
                
            conn.commit()
            print(f"Successfully updated {pool_updated} rows in cards_pool.")
            print(f"Successfully updated {inv_updated} rows in inventory.")
            
    except Exception as e:
        conn.rollback()
        print(f"Database error: {e}")
    finally:
        release_connection(conn)

if __name__ == "__main__":
    run()
