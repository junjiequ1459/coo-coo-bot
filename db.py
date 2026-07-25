import os
import time
from psycopg2.pool import SimpleConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None

def init_pool():
    global _pool
    if _pool is not None:
        return
    for attempt in range(3):
        try:
            _pool = SimpleConnectionPool(1, 5, dsn=DATABASE_URL)
            print("✅ PostgreSQL connection pool initialized!")
            return
        except Exception as e:
            print(f"⚠️ DB pool init attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(2)
    print("❌ Could not initialize DB pool after 3 attempts")

def get_connection():
    if _pool is None:
        init_pool()
    if _pool is None:
        raise Exception("Database connection pool not available")
    conn = _pool.getconn()
    conn.autocommit = False
    return conn

def release_connection(conn):
    if _pool is None:
        return
    try:
        conn.rollback()
    except Exception:
        pass
    try:
        _pool.putconn(conn)
    except Exception:
        pass
