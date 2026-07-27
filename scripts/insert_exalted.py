import json
import psycopg2
import sys
import os
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_connection, release_connection

def insert_exalted_cards():
    conn = get_connection()
    cur = conn.cursor()
    
    with open("scripts/preview_exalted.json", "r") as f:
        data = json.load(f)
        
    inserted_count = 0
    for item in data:
        # Check if already exists just in case
        cur.execute("SELECT 1 FROM cards_pool WHERE character_name = %s AND series_name = %s", (item["character_name"], item["series_name"]))
        if cur.fetchone():
            continue
            
        cur.execute("""
            INSERT INTO cards_pool (character_name, series_name, image_url, rarity, favourites)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            item["character_name"],
            item["series_name"],
            item["image_url"],
            "Exalted",
            item["favourites"]
        ))
        inserted_count += 1
        
    conn.commit()
    release_connection(conn)
    print(f"Successfully injected {inserted_count} Exalted cards into the cards_pool database!")

if __name__ == "__main__":
    insert_exalted_cards()
