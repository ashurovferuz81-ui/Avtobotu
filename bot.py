import os
import sqlite3
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- SOZLAMALAR ---
MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579 # Sizning ID

logging.basicConfig(level=logging.INFO)
main_dp = Dispatcher()

# --- DATABASE ---
conn = sqlite3.connect("kino_builder.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS my_bots (
    owner_id INTEGER PRIMARY KEY, 
    token TEXT UNIQUE, 
    is_premium INTEGER DEFAULT 0, 
    created_at TEXT,
    sub_channel TEXT DEFAULT '@Sardorbeko008'
)""")
cur.execute("CREATE TABLE IF NOT EXISTS movies (bot_token TEXT, code TEXT, file_id TEXT)")
conn.commit()

# --- FOYDALANUVCHI BOTLARI MANTIQI ---
async def run_user_bot(token, owner_id):
    try:
        u_bot = Bot(token=token)
        # Webhookni tozalash (Telegram javob berishi uchun shart!)
        await u_bot.delete_webhook(drop_pending_updates=True)
        u_dp = Dispatcher()

        @u_dp.message(Command("start"))
        async def u_start(m: types.Message):
            # 7 kunlik limit tekshiruvi
            res = cur.execute("SELECT created_at, is_premium FROM my_bots WHERE token=?", (token,)).fetchone()
            created_at = datetime.strptime(res[0], '%Y-%m-%d')
            is_premium = res[1]
            days_passed = (datetime.now() - created_at).days

            if not is_premium and days_passed > 7:
                return await m.answer("⚠️ Bot muddati tugagan! Premium olish uchun asosiy botga murojaat qiling.")

            if m.from_user.id == owner_id:
                kb = types.ReplyKeyboardMarkup(keyboard=[
                    [types.KeyboardButton(text="➕ Kino qo'shish"), types.KeyboardButton(text="🗑 O'chirish")],
                    [types.KeyboardButton(text="📊 Statistika")]
                ], resize_keyboard=True)
                await m.answer("🛠 Admin panel:", reply_markup=kb)
            else:
                await m.answer("🎬 Kino kodini yuboring:")

        @u_dp.message(F.video, F.from_user.id == owner_id)
        async def add_mov(m: types.Message):
            if m.caption and m.caption.isdigit():
                cur.execute("INSERT OR REPLACE INTO movies VALUES (?, ?, ?)", (token, m.caption, m.video.file_id))
                conn.commit()
                await m.answer(f"✅ Saqlandi! Kod: {m.caption}")
            else:
                await m.answer("❌ Video ostiga faqat RAQAM yozing!")

        @u_dp.message(F.text == "🗑 O'chirish", F.from_user.id == owner_id)
        async def del_mov_ask(m: types.Message):
            await m.answer("O'chirmoqchi bo'lgan kodni yuboring:")

        @u_dp.message(F.text.isdigit())
        async def u_handler(m: types.Message):
            # Agar egasi bo'lsa va o'chirishni xohlasa
            if m.from_user.id == owner_id:
                # Avval o'chirib ko'ramiz
                cur.execute("DELETE FROM movies WHERE bot_token=? AND code=?", (token, m.text))
                conn.commit()
                # Keyin qidirib ko'ramiz (agar o'chmagan bo'lsa)
            
            res = cur.execute("SELECT file_id FROM movies WHERE bot_token=? AND code=?", (token, m.text)).fetchone()
            if res:
                await m.answer_video(res[0], caption=f"🎬 Kod: {m.text}")
            else:
                await m.answer("❌ Topilmadi.")

        await u_dp.start_polling(u_bot)
    except Exception as e:
        logging.error(f"Botda xato ({token[:10]}): {e}")

# --- ASOSIY BUILDER ADMIN ---
@main_dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def builder_admin(m: types.Message):
    kb = types.ReplyKeyboardMarkup(keyboard=[
        [types.KeyboardButton(text="📊 Jami botlar"), types.KeyboardButton(text="💎 Prem Berish")],
        [types.KeyboardButton(text="📢 Reklama")]
    ], resize_keyboard=True)
    await m.answer("⚙️ Builder Admin:", reply_markup=kb)

@main_dp.message(F.text == "📊 Jami botlar", F.from_user.id == ADMIN_ID)
async def b_stats(m: types.Message):
    count = cur.execute("SELECT COUNT(*) FROM my_bots").fetchone()[0]
    await m.answer(f"👥 Jami botlar soni: {count}")

@main_dp.message(F.text == "💎 Prem Berish", F.from_user.id == ADMIN_ID)
async def b_prem(m: types.Message):
    await m.answer("Premium berish uchun foydalanuvchi ID yuboring:")

@main_dp.message(F.text.isdigit(), F.from_user.id == ADMIN_ID)
async def b_process_prem(m: types.Message):
    cur.execute("UPDATE my_bots SET is_premium=1 WHERE owner_id=?", (int(m.text),))
    conn.commit()
    await m.answer(f"✅ ID {m.text} ga Premium berildi!")

# --- BOT YARATISH ---
@main_dp.message(Command("start"))
async def main_start(m: types.Message):
    await m.answer("👋 Kino Bot Builder!\n\nToken yuboring va o'z botingizni oling.\nBepul muddat: 7 kun.")

@main_dp.message(F.text.contains(":"))
async def create_bot(m: types.Message):
    token = m.text.strip()
    date = datetime.now().strftime('%Y-%m-%d')
    try:
        cur.execute("INSERT INTO my_bots (owner_id, token, created_at) VALUES (?, ?, ?)", (m.from_user.id, token, date))
        conn.commit()
        asyncio.create_task(run_user_bot(token, m.from_user.id))
        await m.answer("✅ Botingiz yoqildi! @BotFather dan botingizga o'ting.")
    except:
        await m.answer("❌ Bu token band yoki xato.")

async def main():
    m_bot = Bot(token=MAIN_TOKEN)
    await m_bot.delete_webhook(drop_pending_updates=True) # MUHIM!
    
    # Avvalgi botlarni yoqish
    cur.execute("SELECT token, owner_id FROM my_bots")
    for row in cur.fetchall():
        asyncio.create_task(run_user_bot(row[0], row[1]))
    
    await main_dp.start_polling(m_bot)

if __name__ == "__main__":
    asyncio.run(main())
