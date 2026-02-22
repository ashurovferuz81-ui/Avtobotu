import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from database import db
from user_bot import UserBotInstance

MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
main_bot = Bot(token=MAIN_TOKEN)
main_dp = Dispatcher()

@main_dp.message(Command("start"))
async def main_start(m: types.Message):
    await m.answer("🚀 Kino Bot Builder! Token yuboring.")

@main_dp.message(F.text.contains(":"))
async def create_bot(m: types.Message):
    token = m.text.strip()
    db.add_bot(m.from_user.id, token)
    
    # Yangi botni fonda ishga tushirish
    new_bot = UserBotInstance(token, m.from_user.id)
    asyncio.create_task(new_bot.start())
    await m.answer("✅ Botingiz yoqildi!")

async def main():
    await main_bot.delete_webhook(drop_pending_updates=True)
    
    # Bazadagi eski botlarni qayta yoqish
    db.cur.execute("SELECT token, owner_id FROM my_bots")
    for row in db.cur.fetchall():
        old_bot = UserBotInstance(row[0], row[1])
        asyncio.create_task(old_bot.start())
    
    print("Builder bot va barcha foydalanuvchi botlari ishga tushdi...")
    await main_dp.start_polling(main_bot)

if __name__ == "__main__":
    asyncio.run(main())
