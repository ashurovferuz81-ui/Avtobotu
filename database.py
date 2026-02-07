import psycopg2
from config import DATABASE_URL

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id BIGINT PRIMARY KEY,
    is_premium BOOLEAN DEFAULT FALSE
)
""")
conn.commit()

def add_user(user_id):
    cursor.execute(
        "INSERT INTO users (id) VALUES (%s) ON CONFLICT DO NOTHING",
        (user_id,)
    )
    conn.commit()

def set_premium(user_id):
    cursor.execute(
        "UPDATE users SET is_premium=TRUE WHERE id=%s",
        (user_id,)
    )
    conn.commit()

def get_all_users():
    cursor.execute("SELECT id FROM users")
    return cursor.fetchall()
