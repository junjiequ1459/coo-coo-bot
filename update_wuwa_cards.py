import requests
from db import get_connection, release_connection
import sys

API_URL = "https://wutheringwaves.fandom.com/api.php"

def run():
    print("Connecting to database...")
    conn = get_connection()
    updates = {}
    missing = []
    try:
        with conn.cursor() as cur:
            # Select ALL characters
            cur.execute("SELECT DISTINCT character_name FROM cards_pool WHERE series_name ILIKE %s", ('%Wuthering Waves%',))
            rows = cur.fetchall()
            characters = [r[0] for r in rows]
            print(f"Found {len(characters)} characters.")
            
            batch_size = 15
            for i in range(0, len(characters), batch_size):
                batch = characters[i:i+batch_size]
                titles = []
                for c in batch:
                    safe_c = c.replace(' ', '_')
                    titles.append(f"File:{safe_c}_Card.jpg")
                    titles.append(f"File:{safe_c}_Card.png")
                    titles.append(f"File:{safe_c}_Card.webp")
                
                titles_str = "|".join(titles)
                
                params = {
                    "action": "query",
                    "prop": "imageinfo",
                    "iiprop": "url",
                    "format": "json",
                    "titles": titles_str
                }
                
                resp = requests.get(API_URL, params=params)
                if resp.status_code != 200:
                    print(f"Failed to fetch API: {resp.status_code}")
                    continue
                    
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                
                for page_id, page_info in pages.items():
                    title = page_info.get("title", "")
                    if "imageinfo" in page_info:
                        url = page_info["imageinfo"][0]["url"]
                        raw_name = title.replace("File:", "").replace(" Card.jpg", "").replace(" Card.png", "").replace(" Card.webp", "")
                        
                        matched_char = next((c for c in batch if c.lower() == raw_name.lower()), None)
                        
                        if matched_char and matched_char not in updates:
                            for ext in [".jpg", ".png", ".webp"]:
                                if ext in url:
                                    clean_url = url.split(ext)[0] + ext
                                    updates[matched_char] = clean_url
                                    break
            
            # Find missing characters
            for c in characters:
                if c not in updates:
                    missing.append(c)
            
            print(f"Found Card image for {len(updates)} characters.")
            if missing:
                print(f"Could not find Card image for {len(missing)} characters:")
                for m in missing[:10]:
                    print(f" - {m}")
                
            # Update cards_pool
            pool_updated = 0
            for char_name, url in updates.items():
                cur.execute(
                    "UPDATE cards_pool SET image_url = %s WHERE series_name ILIKE %s AND character_name = %s",
                    (url, '%Wuthering Waves%', char_name)
                )
                pool_updated += cur.rowcount
            
            # Update inventory
            inv_updated = 0
            for char_name, url in updates.items():
                cur.execute(
                    "UPDATE inventory SET image_url = %s WHERE series_name ILIKE %s AND character_name = %s",
                    (url, '%Wuthering Waves%', char_name)
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
