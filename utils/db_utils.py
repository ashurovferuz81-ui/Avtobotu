import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

# --- Movies ---
def add_movie(code, file_id, name):
    cur.execute("INSERT INTO movies (code,file_id,name) VALUES (%s,%s,%s) ON CONFLICT (code) DO UPDATE SET file_id=EXCLUDED.file_id,name=EXCLUDED.name", (code,file_id,name))
    conn.commit()

def del_movie(code):
    cur.execute("DELETE FROM movies WHERE code=%s",(code,))
    conn.commit()

def get_movie(code):
    cur.execute("SELECT file_id,name,views FROM movies WHERE code=%s",(code,))
    return cur.fetchone()

def inc_view(code):
    cur.execute("UPDATE movies SET views = views + 1 WHERE code=%s",(code,))
    conn.commit()

def get_all_movies():
    cur.execute("SELECT * FROM movies")
    return cur.fetchall()

# --- Channels ---
def add_channel(channel):
    cur.execute("INSERT INTO channels (channel) VALUES (%s) ON CONFLICT DO NOTHING",(channel,))
    conn.commit()

def del_channel(channel):
    cur.execute("DELETE FROM channels WHERE channel=%s",(channel,))
    conn.commit()

def get_all_channels():
    cur.execute("SELECT channel FROM channels")
    return [i['channel'] for i in cur.fetchall()]

# --- Users ---
def add_user(user_id, username):
    cur.execute("INSERT INTO users (user_id,username) VALUES (%s,%s) ON CONFLICT DO NOTHING",(user_id,username))
    conn.commit()

def get_all_users():
    cur.execute("SELECT * FROM users")
    return cur.fetchall()
