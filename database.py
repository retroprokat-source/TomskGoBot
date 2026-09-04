import sqlite3
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Пользователи
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Маршруты
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            price TEXT,
            duration TEXT,
            distance TEXT
        )
    """)

    # Точки маршрутов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id TEXT,
            order_num INTEGER,
            name TEXT,
            address TEXT,
            description TEXT,
            photo_file_id TEXT
        )
    """)

    # Прогресс пользователя
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id TEXT,
            route_id TEXT,
            current_point INTEGER DEFAULT 1,
            is_completed BOOLEAN DEFAULT 0,
            PRIMARY KEY (user_id, route_id)
        )
    """)

    # Покупки
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            user_id TEXT,
            route_id TEXT,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, route_id)
        )
    """)

    # Платежи
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            route_id TEXT,
            amount REAL,
            purpose TEXT,
            status TEXT DEFAULT 'pending',
            payment_link_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def add_user(user_id: str, username: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
        (user_id, username)
    )
    conn.commit()
    conn.close()

def add_purchase(user_id: str, route_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO purchases (user_id, route_id) VALUES (?, ?)",
        (user_id, route_id)
    )
    conn.commit()
    conn.close()

def has_purchase(user_id: str, route_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM purchases WHERE user_id = ? AND route_id = ?",
        (user_id, route_id)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_progress(user_id: str, route_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM user_progress WHERE user_id = ? AND route_id = ?",
        (user_id, route_id)
    )
    result = cursor.fetchone()
    conn.close()
    return result

def save_progress(user_id: str, route_id: str, current_point: int, is_completed: int = 0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_progress (user_id, route_id, current_point, is_completed)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, route_id)
        DO UPDATE SET current_point = excluded.current_point,
                      is_completed = excluded.is_completed
        """,
        (user_id, route_id, current_point, is_completed)
    )
    conn.commit()
    conn.close()

def reset_progress(user_id: str, route_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_progress WHERE user_id = ? AND route_id = ?",
        (user_id, route_id)
    )
    conn.commit()
    conn.close()

def get_purchased_routes(user_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.* FROM routes r
        JOIN purchases p ON r.id = p.route_id
        WHERE p.user_id = ?
        """,
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_payment(user_id, route_id, amount, purpose, payment_link_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO payments (user_id, route_id, amount, purpose, status, payment_link_id)
        VALUES (?, ?, ?, ?, 'pending', ?)
        """,
        (user_id, route_id, amount, purpose, payment_link_id)
    )
    conn.commit()
    conn.close()

def get_payment_by_link_id(payment_link_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM payments WHERE payment_link_id = ?",
        (payment_link_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result

def update_payment_status(payment_link_id: str, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE payments SET status = ? WHERE payment_link_id = ?",
        (status, payment_link_id)
    )
    conn.commit()
    conn.close()
