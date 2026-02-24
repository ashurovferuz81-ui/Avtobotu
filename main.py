import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- SOZLAMALAR ---
ADMIN_ID = 5775388579
MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"

logging.basicConfig(level=logging.INFO)

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect('builder.db')
    cursor = conn.cursor()
    # Botlar jadvali
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_bots 
                      (user_id INTEGER, token TEXT, bot_type TEXT)''')
    # Kinolar jadvali (Har bir bot uchun umumiy yoki alohida qilish mumkin)
    cursor.execute('''CREATE TABLE IF NOT EXISTS movies 
                      (bot_token TEXT, movie_id TEXT, movie_name TEXT)''')
    conn.commit()
    conn.close()

# --- KINO BOT LOGIKASI ---
async def start_kino_bot(token):
    try:
        bot = Bot(token=token)
        dp = Dispatcher()

        @dp.message(Command("start"))
        async def start_cmd(message: types.Message):
            await message.answer("🎬 Xush kelibsiz! Kino kodini yuboring.\nAdmin bo'lsangiz /admin yozing.")

        @dp.message(Command("admin"))
        async def admin_panel(message: types.Message):
            # Bu yerda admin ekanligini tekshirish kerak (builder bazasidan)
            kb = [
                [types.KeyboardButton(text="➕ Kino qo'shish"), types.KeyboardButton(text="📊 Statistika")],
                [types.KeyboardButton(text="📢 Majburiy obuna")]
            ]
            keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
            await message.answer("🔧 Admin boshqaruv paneli:", reply_markup=keyboard)

        # Kino qo'shish (Soddalashtirilgan)
        @dp.message(F.text == "➕ Kino qo'shish")
        async def add_movie_start(message: types.Message):
            await message.answer("Kinoni yuboring (Hozircha faqat kodini yozing, masalan: 101)")

        @dp.message(F.text == "📊 Statistika")
        async def show_stats(message: types.Message):
            await message.answer("📈 Bot a'zolari soni: 124 ta")

        # Kino qidirish logikasi
        @dp.message(F.text.isdigit())
        async def search_movie(message: types.Message):
            code = message.text
            await message.answer(f"🔍 {code}-raqamli kino qidirilmoqda...")
            # Bu yerda bazadan kinoni qidirish kodi bo'ladi

        print(f"✅ Bot ishga tushdi: {token[:15]}...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Xatolik: {token[:10]} botda: {e}")

# --- ASOSIY BUILDER BOT ---
main_bot = Bot(token=MAIN_TOKEN)
main_dp = Dispatcher()

@main_dp.message(Command("start"))
async def main_start(message: types.Message):
    await message.answer("🤖 **Builder Botga xush kelibsiz!**\n\nKino bot ochish uchun @BotFather dan olgan tokenni yuboring.")

@main_dp.message(F.text.contains(":"))
async def register_new_bot(message: types.Message):
    token = message.text.strip()
    
    conn = sqlite3.connect('builder.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_bots VALUES (?, ?, ?)", (message.from_user.id, token, "kino"))
    conn.commit()
    conn.close()

    await message.answer("🚀 Botingiz bazaga qo'shildi va ishga tushmoqda...")
    asyncio.create_task(start_kino_bot(token))

async def main():
    init_db()
    # Avvaldan bazada bor botlarni ham qayta ishga tushirish (agar bot o'chib yonsa)
    conn = sqlite3.connect('builder.db')
    cursor = conn.cursor()
    cursor.execute("SELECT token FROM user_bots")
    bots = cursor.fetchall()
    for b in bots:
        asyncio.create_task(start_kino_bot(b[0]))
    conn.close()

    await main_dp.start_polling(main_bot)

if __name__ == "__main__":
    asyncio.run(main())
