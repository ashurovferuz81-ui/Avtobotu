import os
import sqlite3
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579

logging.basicConfig(level=logging.INFO)
main_dp = Dispatcher()

# --- DATABASE ---
conn = sqlite3.connect("kino_system.db", check_same_thread=False)
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

# --- STATES ---
class UserBotStates(StatesGroup):
    waiting_for_movie = State()
    waiting_for_delete = State()
    waiting_for_channel = State()
    waiting_for_broadcast = State()

# --- FOYDALANUVCHI BOT FUNKSIYASI ---
async def run_user_bot(token, owner_id):
    try:
        u_bot = Bot(token=token)
        await u_bot.delete_webhook(drop_pending_updates=True)
        u_dp = Dispatcher()

        def admin_kb():
            return ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text="➕ Kino qo'shish"), KeyboardButton(text="🗑 Kino o'chirish")],
                [KeyboardButton(text="📢 Kanal sozlash"), KeyboardButton(text="✉️ Xabar yuborish")],
                [KeyboardButton(text="📊 Statistika")]
            ], resize_keyboard=True)

        # 1. Start va Majburiy obuna
        @u_dp.message(Command("start"))
        async def u_start(m: types.Message, state: FSMContext):
            await state.clear()
            res = cur.execute("SELECT sub_channel, created_at, is_premium FROM my_bots WHERE token=?", (token,)).fetchone()
            channel = res[0]
            
            # Muddat tekshirish (7 kun)
            created_at = datetime.strptime(res[1], '%Y-%m-%d')
            if not res[2] and (datetime.now() - created_at).days > 7:
                return await m.answer("⚠️ Bot muddati tugagan. Premium oling.")

            if m.from_user.id == owner_id:
                await m.answer("🛠 Admin panel:", reply_markup=admin_kb())
            else:
                # Obuna tekshirish
                try:
                    chat_member = await u_bot.get_chat_member(chat_id=channel, user_id=m.from_user.id)
                    if chat_member.status in ["left", "kicked"]:
                        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{channel[1:]}")]])
                        return await m.answer(f"Botdan foydalanish uchun {channel} kanaliga a'zo bo'ling!", reply_markup=kb)
                except: pass
                await m.answer("🎬 Kino kodini yuboring:")

        # 2. Kino qo'shish jarayoni
        @u_dp.message(F.text == "➕ Kino qo'shish", F.from_user.id == owner_id)
        async def u_add_start(m: types.Message, state: FSMContext):
            await state.set_state(UserBotStates.waiting_for_movie)
            await m.answer("Kinoni yuboring (Video ostida kodi bo'lsin):")

        @u_dp.message(UserBotStates.waiting_for_movie, F.video)
        async def u_save_movie(m: types.Message, state: FSMContext):
            if m.caption and m.caption.isdigit():
                cur.execute("INSERT OR REPLACE INTO movies VALUES (?, ?, ?, ?)", (token, m.caption, m.video.file_id, m.caption))
                conn.commit()
                await m.answer(f"✅ Kino saqlandi! Kod: {m.caption}")
                await state.clear()
            else:
                await m.answer("❌ Xato! Video ostida faqat raqamli kod bo'lishi shart.")

        # 3. Kino o'chirish
        @u_dp.message(F.text == "🗑 Kino o'chirish", F.from_user.id == owner_id)
        async def u_del_start(m: types.Message, state: FSMContext):
            await state.set_state(UserBotStates.waiting_for_delete)
            await m.answer("O'chirmoqchi bo'lgan kino kodini yuboring:")

        @u_dp.message(UserBotStates.waiting_for_delete)
        async def u_del_confirm(m: types.Message, state: FSMContext):
            cur.execute("DELETE FROM movies WHERE bot_token=? AND code=?", (token, m.text))
            conn.commit()
            await m.answer(f"✅ Kod {m.text} o'chirildi.")
            await state.clear()

        # 4. Kanalni sozlash
        @u_dp.message(F.text == "📢 Kanal sozlash", F.from_user.id == owner_id)
        async def u_chan_start(m: types.Message, state: FSMContext):
            await state.set_state(UserBotStates.waiting_for_channel)
            await m.answer("Yangi kanal username'ini yuboring (Masalan: @mening_kanalim):")

        @u_dp.message(UserBotStates.waiting_for_channel)
        async def u_chan_save(m: types.Message, state: FSMContext):
            if m.text.startswith("@"):
                cur.execute("UPDATE my_bots SET sub_channel=? WHERE token=?", (m.text, token))
                conn.commit()
                await m.answer(f"✅ Kanal o'zgardi: {m.text}")
                await state.clear()
            else: await m.answer("❌ @ belgisi bilan yuboring.")

        # 5. Kino qidirish (Hamma uchun)
        @u_dp.message(F.text.isdigit())
        async def u_search(m: types.Message):
            res = cur.execute("SELECT file_id FROM movies WHERE bot_token=? AND code=?", (token, m.text)).fetchone()
            if res: await m.answer_video(res[0], caption=f"🎬 Kod: {m.text}")
            else: await m.answer("❌ Bu kod bilan kino topilmadi.")

        await u_dp.start_polling(u_bot)
    except Exception as e:
        logging.error(f"Error in user bot: {e}")

# --- BUILDER (ASOSIY) LOGIKA ---
@main_dp.message(Command("start"))
async def b_start(m: types.Message):
    await m.answer("🚀 Kino Bot Builder!\nToken yuboring va o'z botingizni oling.\n7 kun bepul.")

@main_dp.message(F.text.contains(":"))
async def b_create(m: types.Message):
    token = m.text.strip()
    try:
        cur.execute("INSERT INTO my_bots (owner_id, token, created_at) VALUES (?, ?, ?)", 
                    (m.from_user.id, token, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        asyncio.create_task(run_user_bot(token, m.from_user.id))
        await m.answer("✅ Tayyor! @BotFather dan botingizga kiring.")
    except: await m.answer("❌ Xato yoki token band.")

async def main():
    m_bot = Bot(token=MAIN_TOKEN)
    await m_bot.delete_webhook(drop_pending_updates=True)
    cur.execute("SELECT token, owner_id FROM my_bots")
    for row in cur.fetchall():
        asyncio.create_task(run_user_bot(row[0], row[1]))
    await main_dp.start_polling(m_bot)

if __name__ == "__main__":
    asyncio.run(main())
