import os
import psycopg2
from psycopg2 import pool

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None

def init_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)
        print("✅ PostgreSQL connection pool initialized!")

def get_connection():
    if _pool is None:
        init_pool()
    conn = _pool.getconn()
    conn.autocommit = False
    return conn

def release_connection(conn):
    if _pool is None:
        return
    try:
        conn.rollback()  # clean up any uncommitted transaction
    except Exception:
        pass
    _pool.putconn(conn)
