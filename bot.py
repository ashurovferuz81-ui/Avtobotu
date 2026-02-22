import os
import sqlite3
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# --- ASOSIY SOZLAMALAR ---
MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579

logging.basicConfig(level=logging.INFO)
main_dp = Dispatcher()

# --- DATABASE (Railway uchun mustahkam) ---
conn = sqlite3.connect("kinogen_final.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS my_bots (
    owner_id INTEGER PRIMARY KEY, 
    token TEXT UNIQUE, 
    is_premium INTEGER DEFAULT 0, 
    created_at TEXT,
    sub_channel TEXT DEFAULT '@Sardorbeko008'
)""")
cur.execute("CREATE TABLE IF NOT EXISTS movies (bot_token TEXT, code TEXT, file_id TEXT, caption TEXT)")
conn.commit()

# --- FOYDALANUVCHI BOTLARI UCHUN MANTIQ ---
async def run_user_bot(token, owner_id):
    try:
        u_bot = Bot(token=token)
        u_dp = Dispatcher()

        # Admin klaviaturasi
        def admin_kb():
            return ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="🗑 Kino o'chirish")],
                [KeyboardButton(text="📢 Kanalni sozlash"), KeyboardButton(text="📊 Statistika")]
            ], resize_keyboard=True)

        @u_dp.message(Command("start"))
        async def u_start(m: types.Message):
            # Muddat va Obuna tekshiruvi (Yuqoridagi mantiq bilan bir xil)
            res = cur.execute("SELECT created_at, is_premium, sub_channel FROM my_bots WHERE token=?", (token,)).fetchone()
            if m.from_user.id == owner_id:
                await m.answer("🛠 Admin panel:", reply_markup=admin_kb())
            else:
                await m.answer(f"🎥 Kino kodini yuboring (Masalan: 12):")

        # KINO QO'SHISH (Faqat Admin)
        @u_dp.message(F.video, F.from_user.id == owner_id)
        async def u_add_movie(m: types.Message):
            if m.caption and m.caption.isdigit():
                cur.execute("INSERT OR REPLACE INTO movies VALUES (?, ?, ?, ?)", (token, m.caption, m.video.file_id, m.caption))
                conn.commit()
                await m.answer(f"✅ Kino saqlandi! Kod: {m.caption}")
            else:
                await m.answer("⚠️ Iltimos, video ostiga faqat RAQAMLI KOD yozing.")

        # KINO O'CHIRISH (Faqat Admin)
        @u_dp.message(F.text == "🗑 Kino o'chirish", F.from_user.id == owner_id)
        async def u_del_ask(m: types.Message):
            await m.answer("O'chirmoqchi bo'lgan kino kodingizni yuboring:")

        # KANALNI SOZLASH (Faqat Admin)
        @u_dp.message(F.text == "📢 Kanalni sozlash", F.from_user.id == owner_id)
        async def u_set_chan(m: types.Message):
            await m.answer("Yangi kanal nomini yuboring (Masalan: @sizning_kanalingiz):")

        @u_dp.message(F.from_user.id == owner_id)
        async def u_admin_actions(m: types.Message):
            if m.text.startswith("@"): # Kanal sozlash
                cur.execute("UPDATE my_bots SET sub_channel=? WHERE token=?", (m.text, token))
                conn.commit()
                await m.answer(f"✅ Majburiy obuna kanali o'zgardi: {m.text}")
            elif m.text.isdigit(): # Kino o'chirish yoki qidirish
                # Agar o'chirish rejimi bo'lsa (soddalashtirilgan)
                cur.execute("DELETE FROM movies WHERE bot_token=? AND code=?", (token, m.text))
                conn.commit()
                await m.answer(f"🗑 Kod {m.text} bo'yicha kino o'chirildi (agar mavjud bo'lsa).")

        # KINO QIDIRISH (Oddiy foydalanuvchilar uchun)
        @u_dp.message(F.text.isdigit())
        async def u_search(m: types.Message):
            res = cur.execute("SELECT file_id, caption FROM movies WHERE bot_token=? AND code=?", (token, m.text)).fetchone()
            if res:
                await m.answer_video(video=res[0], caption=f"🎬 Kod: {res[1]}")
            else:
                await m.answer("❌ Afsuski, bu kodli kino topilmadi.")

        await u_dp.start_polling(u_bot)
    except Exception as e:
        print(f"Xato botda: {e}")

# --- BUILDER (ASOSIY) ADMIN PANEL ---
@main_dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def builder_admin(m: types.Message):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Botlar ro'yxati"), KeyboardButton(text="📢 Global Reklama")],
        [KeyboardButton(text="💎 Premium Berish"), KeyboardButton(text="⚙️ Kanal Sozlash")]
    ], resize_keyboard=True)
    await m.answer("⚙️ Builder Admin Paneli:", reply_markup=kb)

@main_dp.message(F.text == "💎 Premium Berish", F.from_user.id == ADMIN_ID)
async def ask_prem_id(m: types.Message):
    await m.answer("Premium beriladigan foydalanuvchi ID sini yozing:")

@main_dp.message(F.text.isdigit(), F.from_user.id == ADMIN_ID)
async def builder_give_prem(m: types.Message):
    cur.execute("UPDATE my_bots SET is_premium=1 WHERE owner_id=?", (int(m.text),))
    conn.commit()
    await m.answer(f"✅ Foydalanuvchi {m.text} uchun 7 kunlik limit olib tashlandi (Premium berildi).")

@main_dp.message(F.text == "⚙️ Kanal Sozlash", F.from_user.id == ADMIN_ID)
async def builder_set_chan(m: types.Message):
    await m.answer("Asosiy majburiy obuna kanalini yozing (Masalan: @Sardorbeko008):")

# --- BOT YARATISH ---
@main_dp.message(F.text.contains(":"))
async def main_create_bot(m: types.Message):
    token = m.text.strip()
    date_now = datetime.now().strftime('%Y-%m-%d')
    try:
        cur.execute("INSERT INTO my_bots (owner_id, token, created_at) VALUES (?, ?, ?)", (m.from_user.id, token, date_now))
        conn.commit()
        asyncio.create_task(run_user_bot(token, m.from_user.id))
        await m.answer("✅ Botingiz yaratildi va ishga tushdi!\n\n7 kunlik bepul sinov muddati boshlandi.")
    except:
        await m.answer("⚠️ Bu bot allaqachon tizimimizda bor.")

async def main():
    m_bot = Bot(token=MAIN_TOKEN)
    # Bazadagi barcha botlarni Railway yonganda qayta ishga tushirish
    cur.execute("SELECT token, owner_id FROM my_bots")
    rows = cur.fetchall()
    for row in rows:
        asyncio.create_task(run_user_bot(row[0], row[1]))
    
    await main_dp.start_polling(m_bot)

if __name__ == "__main__":
    asyncio.run(main())
