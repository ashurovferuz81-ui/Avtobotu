import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

API_TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def db_init():
    conn = sqlite3.connect("quran_ai.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    # Kinolar jadvali: nomi, kodi (file_id), janri
    cur.execute("CREATE TABLE IF NOT EXISTS lessons (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, file_id TEXT, genre TEXT)")
    conn.commit()
    conn.close()

@dp.message(Command("start"))
async def start(message: types.Message):
    conn = sqlite3.connect("quran_ai.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer(f"Xush kelibsiz! Fillover115 kino portaliga.")

async def bot_main():
    db_init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(bot_main())
