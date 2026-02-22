import os
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# --- ASOSIY SOZLAMALAR ---
MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579 # SIZNING ID

logging.basicConfig(level=logging.INFO)
main_dp = Dispatcher()

# --- DATABASE ---
conn = sqlite3.connect("kinogen_v3.db", check_same_thread=False)
cur = conn.cursor()
# Foydalanuvchilar va botlar (created_at qo'shildi)
cur.execute("""CREATE TABLE IF NOT EXISTS my_bots (
    owner_id INTEGER PRIMARY KEY, 
    token TEXT UNIQUE, 
    is_premium INTEGER DEFAULT 0, 
    created_at TEXT,
    sub_channel TEXT DEFAULT '@Sardorbeko008'
)""")
# Kinolar
cur.execute("CREATE TABLE IF NOT EXISTS movies (bot_token TEXT, code TEXT, file_id TEXT, caption TEXT)")
conn.commit()

# --- MAJBURIY OBUNA TEKSHIRISH ---
async def check_sub(bot: Bot, user_id, channel):
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status not in ["left", "kicked"]
    except: return True # Agar bot kanalda admin bo'lmasa

# --- FOYDALANUVCHI BOTLARI ---
async def start_user_kino_bot(token, owner_id):
    try:
        u_bot = Bot(token=token)
        u_dp = Dispatcher()

        @u_dp.message(Command("start"))
        async def u_start(m: types.Message):
            # Muddatni tekshirish
            res = cur.execute("SELECT created_at, is_premium, sub_channel FROM my_bots WHERE token=?", (token,)).fetchone()
            created_at = datetime.strptime(res[0], '%Y-%m-%d')
            is_premium = res[1]
            channel = res[2]

            if not is_premium and (datetime.now() - created_at).days > 7:
                return await m.answer("⚠️ Botingiz muddati tugagan. Faollashtirish uchun @Sardorbeko008 ga yozing.")

            # Majburiy obuna
            if not await check_sub(u_bot, m.from_user.id, channel):
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{channel[1:]}")]])
                return await m.answer(f"Botdan foydalanish uchun {channel} kanaliga a'zo bo'ling!", reply_markup=kb)

            if m.from_user.id == owner_id:
                kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="📢 Kanalni o'zgartirish")]], resize_keyboard=True)
                await m.answer("👑 Admin panelingizga xush kelibsiz!", reply_markup=kb)
            else:
                await m.answer("🎥 Kino kodini yuboring:")

        @u_dp.message(F.video, F.from_user.id == owner_id)
        async def add_movie(m: types.Message):
            if m.caption and m.caption.isdigit():
                cur.execute("INSERT OR REPLACE INTO movies VALUES (?, ?, ?, ?)", (token, m.caption, m.video.file_id, m.caption))
                conn.commit()
                await m.answer(f"✅ Kino saqlandi! Kod: {m.caption}")
            else:
                await m.answer("⚠️ Video captioniga faqat RAQAM yozing.")

        @u_dp.message(F.text.isdigit())
        async def get_movie(m: types.Message):
            res = cur.execute("SELECT file_id FROM movies WHERE bot_token=? AND code=?", (token, m.text)).fetchone()
            if res: await m.answer_video(res[0])
            else: await m.answer("❌ Topilmadi.")

        await u_dp.start_polling(u_bot)
    except: pass

# --- BUILDER (ASOSIY) ADMIN PANEL ---
@main_dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def builder_admin(m: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Foydalanuvchilar"), KeyboardButton(text="📢 Reklama yuborish")],
        [KeyboardButton(text="💎 Premium berish")]
    ], resize_keyboard=True)
    await m.answer("🛠 Builder Boshqaruv Paneli:", reply_markup=kb)

@main_dp.message(F.text == "📊 Foydalanuvchilar", F.from_user.id == ADMIN_ID)
async def stats(m: types.Message):
    all_u = cur.execute("SELECT COUNT(*) FROM my_bots").fetchone()[0]
    await m.answer(f"👥 Jami ochilgan botlar: {all_u} ta")

@main_dp.message(F.text == "💎 Premium berish", F.from_user.id == ADMIN_ID)
async def give_prem(m: types.Message):
    await m.answer("Premium berish uchun foydalanuvchi ID sini yuboring:")

@main_dp.message(F.text.isdigit(), F.from_user.id == ADMIN_ID)
async def process_prem(m: types.Message):
    cur.execute("UPDATE my_bots SET is_premium=1 WHERE owner_id=?", (int(m.text),))
    conn.commit()
    await m.answer(f"✅ Foydalanuvchi {m.text} endi Premium!")

# --- BOT OCHISH ---
@main_dp.message(Command("start"))
async def main_start(m: types.Message):
    await m.answer("🛠 **Kino Bot Builder!**\n\n1. O'z botingizni ochish uchun token yuboring.\n2. Birinchi bot bepul (7 kun).\n3. Keyin umrbod Premium - 50,000 so'm.")

@main_dp.message(F.text.contains(":"))
async def setup_bot(m: types.Message):
    token = m.text.strip()
    date_now = datetime.now().strftime('%Y-%m-%d')
    try:
        cur.execute("INSERT INTO my_bots (owner_id, token, created_at) VALUES (?, ?, ?)", (m.from_user.id, token, date_now))
        conn.commit()
        asyncio.create_task(start_user_kino_bot(token, m.from_user.id))
        await m.answer("✅ Botingiz yoqildi! 7 kundan keyin to'lov qilishingiz kerak bo'ladi.")
    except: await m.answer("❌ Bu token band yoki xato.")

async def main():
    m_bot = Bot(token=MAIN_TOKEN)
    cur.execute("SELECT token, owner_id FROM my_bots")
    for row in cur.fetchall():
        asyncio.create_task(start_user_kino_bot(row[0], row[1]))
    await main_dp.start_polling(m_bot)

if __name__ == "__main__":
    asyncio.run(main())
