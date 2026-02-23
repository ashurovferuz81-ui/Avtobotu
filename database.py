import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL")

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        async with self.pool.acquire() as conn:
            # Botlar ro'yxati
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS my_bots (
                    owner_id BIGINT PRIMARY KEY,
                    token TEXT UNIQUE,
                    bot_type TEXT,
                    sub_channel TEXT DEFAULT NULL
                )
            """)
            # Barcha botlar uchun ma'lumotlar (Kino, Musiqa, Ismlar va h.k.)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_content (
                    bot_token TEXT,
                    key_val TEXT,
                    file_id TEXT,
                    description TEXT
                )
            """)

db = Database()
