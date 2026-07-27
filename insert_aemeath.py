import sys
import psycopg2
from db import get_connection, release_connection

def run():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check if it already exists
            cur.execute(
                "SELECT id FROM cards_pool WHERE character_name = %s AND rarity = %s",
                ("Aemeath", "Exalted")
            )
            res = cur.fetchone()
            if not res:
                cur.execute(
                    """
                    INSERT INTO cards_pool (series_name, character_name, rarity, image_url)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        "Wuthering Waves",
                        "Aemeath",
                        "Exalted",
                        "https://static.wikia.nocookie.net/wutheringwaves/images/4/4f/Aemeath_Profile_Convene_Animation.gif"
                    )
                )
                print("Inserted Aemeath into cards_pool.")
            else:
                cur.execute(
                    """
                    UPDATE cards_pool SET image_url = %s WHERE id = %s
                    """,
                    (
                        "https://static.wikia.nocookie.net/wutheringwaves/images/4/4f/Aemeath_Profile_Convene_Animation.gif",
                        res[0]
                    )
                )
                print("Updated existing Aemeath in cards_pool.")
            
            conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

if __name__ == "__main__":
    run()
