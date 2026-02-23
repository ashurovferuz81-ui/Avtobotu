import asyncio, aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from database import init_db
from user_bot import run_user_bot
from datetime import datetime

TOKEN = "8511690084:AAE5bCLOO3rXwsZQNJ3JjjSmNxL-4MMlG80"
ADMIN_ID = 5775388579

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🤖 **Kino Bot Builder**\n\nToken yuboring va o'z botingizga ega bo'ling!")

@dp.message(F.text.contains(":"))
async def create_bot(m: types.Message):
    token = m.text.strip()
    date = datetime.now().strftime('%Y-%m-%d')
    async with aiosqlite.connect("kino_system.db") as db:
        await db.execute("INSERT OR REPLACE INTO my_bots (owner_id, token, created_at) VALUES (?, ?, ?)", (m.from_user.id, token, date))
        await db.commit()
    asyncio.create_task(run_user_bot(token, m.from_user.id))
    await m.answer("✅ Botingiz ishga tushdi! Endi o'z botingizda adminlik qilishingiz mumkin.")

async def main():
    await init_db()
    async with aiosqlite.connect("kino_system.db") as db:
        cursor = await db.execute("SELECT token, owner_id FROM my_bots")
        async for row in cursor:
            asyncio.create_task(run_user_bot(row[0], row[1]))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
