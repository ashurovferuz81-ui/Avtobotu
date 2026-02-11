import asyncpg
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

# ==== DB INIT ====
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    # Userlar
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id BIGINT PRIMARY KEY,
        username TEXT
    )
    """)
    # Kinolar
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS movies(
        code TEXT PRIMARY KEY,
        file_id TEXT,
        name TEXT,
        views BIGINT DEFAULT 0
    )
    """)
    # Kanallar
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS channels(
        channel TEXT PRIMARY KEY
    )
    """)
    await conn.close()

# ==== USER FUNCTIONS ====
async def add_user(user_id, username):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("INSERT INTO users(user_id, username) VALUES($1,$2) ON CONFLICT DO NOTHING", user_id, username)
    await conn.close()

async def get_all_users():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT user_id, username FROM users")
    await conn.close()
    return rows

# ==== MOVIE FUNCTIONS ====
async def add_movie(code, file_id, name):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("INSERT INTO movies(code, file_id, name) VALUES($1,$2,$3) ON CONFLICT(code) DO UPDATE SET file_id=$2, name=$3", code, file_id, name)
    await conn.close()

async def del_movie(code):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM movies WHERE code=$1", code)
    await conn.close()

async def get_movie(code):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT file_id,name,views FROM movies WHERE code=$1", code)
    await conn.close()
    return row

async def increase_movie_views(code):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE movies SET views = views + 1 WHERE code=$1", code)
    await conn.close()

# ==== CHANNEL FUNCTIONS ====
async def add_channel(channel):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("INSERT INTO channels(channel) VALUES($1) ON CONFLICT DO NOTHING", channel)
    await conn.close()

async def del_channel(channel):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM channels WHERE channel=$1", channel)
    await conn.close()

async def get_all_channels():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT channel FROM channels")
    await conn.close()
    return [r['channel'] for r in rows]
