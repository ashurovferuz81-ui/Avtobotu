import aiosqlite
from datetime import datetime

DB = "kino_system.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        # sub_channel har bir bot uchun alohida saqlanadi
        await db.execute("""CREATE TABLE IF NOT EXISTS my_bots (
            owner_id INTEGER PRIMARY KEY, 
            token TEXT UNIQUE, 
            is_premium INTEGER DEFAULT 0, 
            created_at TEXT,
            sub_channel TEXT DEFAULT NULL
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS movies (
            bot_token TEXT,
            code TEXT,
            file_id TEXT
        )""")
        await db.commit()
