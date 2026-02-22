import os
import sqlite3
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- SOZLAMALAR ---
MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579

logging.basicConfig(level=logging.INFO)
main_dp = Dispatcher()

# --- DATABASE ---
conn = sqlite3.connect("kinogen.db", check_same_thread=False)
cur = conn.cursor()
# Botlar jadvali
cur.execute("CREATE TABLE IF NOT EXISTS my_bots (owner_id INTEGER, token TEXT UNIQUE)")
# Kinolar jadvali (Hamma botlar uchun bitta umumiy baza yoki alohida qilish mumkin)
cur.execute("CREATE TABLE IF NOT EXISTS movies (code TEXT PRIMARY KEY, file_id TEXT, caption TEXT)")
conn.commit()

# --- FOYDALANUVCHI BOTLARI UCHUN MANTIQ ---
async def start_user_kino_bot(token):
    try:
        u_bot = Bot(token=token)
        u_dp = Dispatcher()

        @u_dp.message(Command("start"))
        async def u_start(m: types.Message):
            await m.answer("👋 Kino botga xush kelibsiz!\nKino kodini yuboring:")

        @u_dp.message(F.text.isdigit()) # Faqat raqam (kod) yuborilsa
        async def get_movie(m: types.Message):
            code = m.text
            res = cur.execute("SELECT file_id, caption FROM movies WHERE code=?", (code,)).fetchone()
            if res:
                await m.answer_video(video=res[0], caption=res[1])
            else:
                await m.answer("😔 Bu kod bilan kino topilmadi.")

        # Botni fonda ishga tushirish
        await u_dp.start_polling(u_bot)
    except Exception as e:
        logging.error(f"Bot {token[:10]} xatosi: {e}")

# --- ASOSIY BOT (CREATOR) MANTIQI ---
@main_dp.message(Command("start"))
async def main_start(m: types.Message):
    await m.answer(
        "🚀 **Kino Bot Creator**-ga xush kelibsiz!\n\n"
        "O'z kino botingizni ochish uchun @BotFather-dan token oling va menga yuboring.\n"
        "Siz ochgan botda bizning bazadagi barcha kinolar ishlaydi!"
    )

@main_dp.message(F.text.contains(":")) # Token qabul qilish
async def create_bot(m: types.Message):
    token = m.text.strip()
    try:
        cur.execute("INSERT INTO my_bots (owner_id, token) VALUES (?, ?)", (m.from_user.id, token))
        conn.commit()
        asyncio.create_task(start_user_kino_bot(token))
        await m.answer("✅ Botingiz ishga tushdi! Endi o'z botingizga o'tib start bosing.")
    except:
        await m.answer("❌ Bu bot allaqachon tizimda bor.")

# --- ADMIN UCHUN KINO QO'SHISH ---
@main_dp.message(F.video, F.from_user.id == ADMIN_ID)
async def add_movie(m: types.Message):
    # Video caption-da kod yozilgan bo'lishi kerak (masalan: 125)
    if m.caption and m.caption.isdigit():
        code = m.caption
        file_id = m.video.file_id
        cur.execute("INSERT OR REPLACE INTO movies (code, file_id, caption) VALUES (?, ?, ?)", 
                    (code, file_id, f"Kino kodi: {code}"))
        conn.commit()
        await m.answer(f"✅ Kino bazaga qo'shildi! Kod: {code}")
    else:
        await m.answer("❌ Kinoni caption (tavsif) qismiga faqat raqamli kod yozib yuboring!")

# --- TIZIMNI YURGIZISH ---
async def main():
    m_bot = Bot(token=MAIN_TOKEN)
    # Avvalgi botlarni qayta yoqish
    cur.execute("SELECT token FROM my_bots")
    for row in cur.fetchall():
        asyncio.create_task(start_user_kino_bot(row[0]))
    
    await main_dp.start_polling(m_bot)

if __name__ == "__main__":
    asyncio.run(main())
