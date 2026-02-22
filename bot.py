import os
import sqlite3
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- SOZLAMALAR ---
MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579 # Asosiy bot egasi (Siz)

logging.basicConfig(level=logging.INFO)
main_dp = Dispatcher()

# --- DATABASE ---
conn = sqlite3.connect("kinogen_v2.db", check_same_thread=False)
cur = conn.cursor()
# Botlar va ularning egalari
cur.execute("CREATE TABLE IF NOT EXISTS my_bots (owner_id INTEGER, token TEXT UNIQUE)")
# Har bir bot uchun alohida kinolar (bot_token bilan bog'langan)
cur.execute("CREATE TABLE IF NOT EXISTS movies (bot_token TEXT, code TEXT, file_id TEXT, caption TEXT)")
conn.commit()

# --- FOYDALANUVCHI BOTLARI UCHUN MANTIQ ---
async def start_user_kino_bot(token, owner_id):
    try:
        u_bot = Bot(token=token)
        u_dp = Dispatcher()

        # Admin panel tugmalari
        def admin_kb():
            return types.ReplyKeyboardMarkup(keyboard=[
                [types.KeyboardButton(text="➕ Kino qo'shish"), types.KeyboardButton(text="📊 Statistika")]
            ], resize_keyboard=True)

        @u_dp.message(Command("start"))
        async def u_start(m: types.Message):
            if m.from_user.id == owner_id:
                await m.answer(f"👑 Salom bot egasi! Admin panelingizga xush kelibsiz.", reply_markup=admin_kb())
            else:
                await m.answer("👋 Kino kodini yuboring va kinoni tomosha qiling!")

        # Faqat bot egasi kino qo'sha oladi
        @u_dp.message(F.video, F.from_user.id == owner_id)
        async def add_movie_to_own_bot(m: types.Message):
            if m.caption and m.caption.isdigit():
                code = m.caption
                file_id = m.video.file_id
                cur.execute("INSERT OR REPLACE INTO movies (bot_token, code, file_id, caption) VALUES (?, ?, ?, ?)", 
                            (token, code, file_id, f"Kino kodi: {code}"))
                conn.commit()
                await m.answer(f"✅ Botingizga yangi kino qo'shildi! Kod: {code}")
            else:
                await m.answer("⚠️ Kinoni caption (tavsif) qismiga faqat raqamli kod yozib yuboring!")

        # Kino qidirish (Hamma uchun)
        @u_dp.message(F.text.isdigit())
        async def search_movie(m: types.Message):
            code = m.text
            res = cur.execute("SELECT file_id, caption FROM movies WHERE bot_token=? AND code=?", (token, code)).fetchone()
            if res:
                await m.answer_video(video=res[0], caption=res[1])
            else:
                await m.answer("❌ Kechirasiz, bu botda bunday kodli kino yo'q.")

        @u_dp.message(F.text == "📊 Statistika", F.from_user.id == owner_id)
        async def u_stats(m: types.Message):
            count = cur.execute("SELECT COUNT(*) FROM movies WHERE bot_token=?", (token,)).fetchone()[0]
            await m.answer(f"📁 Sizning botingizda jami {count} ta kino bor.")

        await u_dp.start_polling(u_bot)
    except Exception as e:
        logging.error(f"Xato: {e}")

# --- ASOSIY BOT (BUILDER) ---
@main_dp.message(Command("start"))
async def main_start(m: types.Message):
    await m.answer("🛠 **Kino Bot Builder!**\n\nO'z botingizni ochish uchun token yuboring.\n"
                   "Botingiz ochilgach, unga video yuborsangiz, u o'sha kinoni bazasiga qo'shib oladi!")

@main_dp.message(F.text.contains(":"))
async def create_user_bot(m: types.Message):
    token = m.text.strip()
    try:
        cur.execute("INSERT INTO my_bots (owner_id, token) VALUES (?, ?)", (m.from_user.id, token))
        conn.commit()
        asyncio.create_task(start_user_kino_bot(token, m.from_user.id))
        await m.answer(f"✅ Botingiz tayyor!\nLink: @{(await Bot(token=token).get_me()).username}\n\n"
                       f"Botingizga o'ting va video yuborib kod bering.")
    except:
        await m.answer("❌ Bu bot allaqachon ro'yxatdan o'tgan.")

async def main():
    m_bot = Bot(token=MAIN_TOKEN)
    # Oldingi botlarni egalari bilan qayta yuklash
    cur.execute("SELECT token, owner_id FROM my_bots")
    for row in cur.fetchall():
        asyncio.create_task(start_user_kino_bot(row[0], row[1]))
    
    await main_dp.start_polling(m_bot)

if __name__ == "__main__":
    asyncio.run(main())
