import requests
from bs4 import BeautifulSoup
from db import get_connection, release_connection
import sys
import concurrent.futures

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_profile_footer(char_name):
    # Fandom wiki URLs usually replace spaces with underscores
    url_name = char_name.replace(" ", "_")
    
    # Handle special cases like 'Yangyang: Xuanling' if necessary, but Fandom handles redirects well usually
    # or it might be Yangyang/Xuanling. We'll try the exact name with underscores.
    
    url = f"https://wutheringwaves.fandom.com/wiki/{url_name}/Gallery"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return char_name, None
            
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Look for images with data-image-name containing "Profile Footer"
        for img in soup.find_all("img"):
            name = img.get("data-image-name", "")
            if "Profile Footer" in name or "_Profile_Footer" in name:
                # Get src or data-src
                src = img.get("data-src") or img.get("src")
                if src:
                    # Clean up URL to get full resolution
                    # Fandom URLs format: .../Name.jpg/revision/latest/scale-to-width-down/123?cb=...
                    # We want just up to the extension
                    if ".jpg" in src:
                        clean = src.split(".jpg")[0] + ".jpg"
                        return char_name, clean
                    elif ".png" in src:
                        clean = src.split(".png")[0] + ".png"
                        return char_name, clean
                    elif ".webp" in src:
                        clean = src.split(".webp")[0] + ".webp"
                        return char_name, clean
                        
        return char_name, None
    except Exception as e:
        print(f"Error fetching {char_name}: {e}")
        return char_name, None

def run():
    print("Connecting to database...")
    conn = get_connection()
    updates = {}
    missing = []
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT character_name FROM cards_pool WHERE series_name ILIKE %s", ('%Wuthering Waves%',))
            rows = cur.fetchall()
            characters = [r[0] for r in rows]
            
        print(f"Found {len(characters)} characters. Scraping galleries...")
        
        # Concurrently scrape galleries
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(fetch_profile_footer, characters)
            
        for char_name, url in results:
            if url:
                updates[char_name] = url
            else:
                missing.append(char_name)
                
        print(f"\nSuccessfully found Profile Footer for {len(updates)} characters.")
        if missing:
            print(f"Could not find Profile Footer for {len(missing)} characters:")
            print(", ".join(missing))
            
        if not updates:
            print("No updates to perform. Exiting.")
            sys.exit(0)
            
        # Perform DB updates
        with conn.cursor() as cur:
            pool_updated = 0
            inv_updated = 0
            
            for char_name, url in updates.items():
                cur.execute(
                    "UPDATE cards_pool SET image_url = %s WHERE series_name ILIKE %s AND character_name = %s",
                    (url, '%Wuthering Waves%', char_name)
                )
                pool_updated += cur.rowcount
                
                cur.execute(
                    "UPDATE inventory SET image_url = %s WHERE series_name ILIKE %s AND character_name = %s",
                    (url, '%Wuthering Waves%', char_name)
                )
                inv_updated += cur.rowcount
                
            conn.commit()
            print(f"\nUpdated {pool_updated} cards_pool rows.")
            print(f"Updated {inv_updated} inventory rows.")
            
    except Exception as e:
        conn.rollback()
        print(f"Database error: {e}")
    finally:
        release_connection(conn)

if __name__ == "__main__":
    run()
