import time

from config import DROP_COOLDOWN_SEC, GRAB_COOLDOWN_SEC
from db import get_connection, release_connection


def get_user_gems(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT gems FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, 0, 0)", (user_id,))
        conn.commit()
        gems = 0
    else:
        gems = row[0]
    release_connection(conn)
    return gems

def get_user_dust(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dust FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, 0, 0)", (user_id,))
        conn.commit()
        dust = 0
    else:
        dust = row[0] if row[0] is not None else 0
    release_connection(conn)
    return dust

def add_user_gems(user_id: int, amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT gems FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        new_gems = max(0, amount)
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, %s, 0)", (user_id, new_gems))
    else:
        new_gems = row[0] + amount
        cursor.execute("UPDATE users SET gems = %s WHERE user_id = %s", (new_gems, user_id))
    conn.commit()
    release_connection(conn)
    return new_gems

def add_user_dust(user_id: int, amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT dust FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    if not row:
        new_dust = amount
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, 0, %s)", (user_id, new_dust))
    else:
        curr = row[0] if row[0] is not None else 0
        new_dust = curr + amount
        cursor.execute("UPDATE users SET dust = %s WHERE user_id = %s", (new_dust, user_id))
    conn.commit()
    release_connection(conn)
    return new_dust

def transfer_gems(from_user_id: int, to_user_id: int, amount: int) -> bool:
    if amount <= 0:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT gems FROM users WHERE user_id = %s", (from_user_id,))
        row1 = cursor.fetchone()
        from_gems = row1[0] if row1 else 0

        if from_gems < amount:
            release_connection(conn)
            return False

        cursor.execute("UPDATE users SET gems = gems - %s WHERE user_id = %s", (amount, from_user_id))

        cursor.execute("SELECT gems FROM users WHERE user_id = %s", (to_user_id,))
        row2 = cursor.fetchone()
        if not row2:
            cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, %s, 0)", (to_user_id, amount))
        else:
            cursor.execute("UPDATE users SET gems = gems + %s WHERE user_id = %s", (amount, to_user_id))

        conn.commit()
        release_connection(conn)
        return True
    except Exception as e:
        print(f"Error transferring gems: {e}")
        conn.rollback()
        release_connection(conn)
        return False

def get_user_cooldowns(user_id: int):
    """Returns timestamps for last_drop, last_grab, last_daily."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_drop, last_grab, last_daily FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    release_connection(conn)
    if not row:
        return 0, 0, 0
    return (row[0] or 0), (row[1] or 0), (row[2] or 0)

def set_user_cooldown(user_id: int, cd_type: str, ts: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, gems, dust) VALUES (%s, 0, 0)", (user_id,))

    if cd_type == "drop":
        cursor.execute("UPDATE users SET last_drop = %s WHERE user_id = %s", (ts, user_id))
    elif cd_type == "grab":
        cursor.execute("UPDATE users SET last_grab = %s WHERE user_id = %s", (ts, user_id))
    elif cd_type == "daily":
        cursor.execute("UPDATE users SET last_daily = %s WHERE user_id = %s", (ts, user_id))
    conn.commit()
    release_connection(conn)

def get_user_premium_until(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT premium_until FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    release_connection(conn)
    if not row or not row[0]:
        return 0
    return row[0]

def is_user_premium(user_id: int) -> bool:
    prem_until = get_user_premium_until(user_id)
    return int(time.time()) < prem_until

def add_user_premium(user_id: int, days: int = 30) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = int(time.time())
    curr_until = get_user_premium_until(user_id)

    start_base = max(now, curr_until)
    new_until = start_base + (days * 86400)

    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, gems, dust, premium_until) VALUES (%s, 0, 0, %s)", (user_id, new_until))
    else:
        cursor.execute("UPDATE users SET premium_until = %s WHERE user_id = %s", (new_until, user_id))

    conn.commit()
    release_connection(conn)
    return new_until

def get_effective_cooldowns(user_id: int):
    """Returns (drop_cd_sec, grab_cd_sec) based on whether user has active Premium Pass."""
    if is_user_premium(user_id):
        return DROP_COOLDOWN_SEC // 2, GRAB_COOLDOWN_SEC // 2
    return DROP_COOLDOWN_SEC, GRAB_COOLDOWN_SEC

def get_user_drop_tickets(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT drop_tickets FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    release_connection(conn)
    if not row or not row[0]:
        return 0
    return row[0]

def add_user_drop_tickets(user_id: int, amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT drop_tickets FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    curr = row[0] if row and row[0] else 0
    new_val = max(0, curr + amount)
    if not row:
        cursor.execute("INSERT INTO users (user_id, gems, dust, drop_tickets) VALUES (%s, 0, 0, %s)", (user_id, new_val))
    else:
        cursor.execute("UPDATE users SET drop_tickets = %s WHERE user_id = %s", (new_val, user_id))
    conn.commit()
    release_connection(conn)
    return new_val

def get_user_grab_tickets(user_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT grab_tickets FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    release_connection(conn)
    if not row or not row[0]:
        return 0
    return row[0]

def add_user_grab_tickets(user_id: int, amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT grab_tickets FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    curr = row[0] if row and row[0] else 0
    new_val = max(0, curr + amount)
    if not row:
        cursor.execute("INSERT INTO users (user_id, gems, dust, grab_tickets) VALUES (%s, 0, 0, %s)", (user_id, new_val))
    else:
        cursor.execute("UPDATE users SET grab_tickets = %s WHERE user_id = %s", (new_val, user_id))
    conn.commit()
    release_connection(conn)
    return new_val
