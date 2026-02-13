import asyncio
import logging
import os
import psycopg2 # PostgreSQL uchun
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                            InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery)

# --- KONFIGURATSIYA ---
API_TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579
# Railway avtomatik DATABASE_URL beradi, agar bo'lmasa pastdagiga o'zingiznikini qo'ying
DB_URL = os.getenv("DATABASE_URL")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- POSTGRESQL BAZA BILAN ISHLASH ---
def get_db_connection():
    conn = psycopg2.connect(DB_URL, sslmode='require')
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Kinolar jadvali
    cur.execute("""CREATE TABLE IF NOT EXISTS movies (
        code INTEGER PRIMARY KEY, 
        file_id TEXT, 
        caption TEXT, 
        views INTEGER DEFAULT 0)""")
    # Foydalanuvchilar jadvali
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, joined_date DATE)")
    # Kanallar jadvali
    cur.execute("CREATE TABLE IF NOT EXISTS channels (id SERIAL PRIMARY KEY, chat_id TEXT, url TEXT, name TEXT)")
    conn.commit()
    cur.close()
    conn.close()

# --- FSM (HOLATLAR) ---
class AdminStates(StatesGroup):
    add_m_video = State()
    add_m_code = State()
    add_m_cap = State()
    del_m_code = State()
    ad_msg = State()
    ad_btn = State()
    chan_id = State()
    chan_url = State()
    chan_name = State()

# --- ADMIN KLAVIATURA ---
def admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Kino Qo'shish"), KeyboardButton(text="🗑 Kino O'chirish")],
        [KeyboardButton(text="📢 Kanal Sozlamalari"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="✉️ Reklama Tarqatish")]
    ], resize_keyboard=True)

# --- OBUNA TEKSHIRISH ---
async def check_sub(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT chat_id, url, name FROM channels")
    chans = cur.fetchall()
    cur.close()
    conn.close()
    
    if not chans: return True
    not_subbed = []
    for cid, url, name in chans:
        try:
            member = await bot.get_chat_member(chat_id=cid, user_id=user_id)
            if member.status in ["left", "kicked"]: not_subbed.append((name, url))
        except: not_subbed.append((name, url))
    return not_subbed if not_subbed else True

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id, joined_date) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING", 
                (message.from_user.id, datetime.now().date()))
    conn.commit()
    cur.close()
    conn.close()
    
    if message.from_user.id == ADMIN_ID:
        await message.answer("Boshqaruv paneli (PostgreSQL):", reply_markup=admin_menu())
    else:
        await message.answer("🍿 <b>Kino kodini yuboring:</b>", parse_mode="HTML")

@dp.message(F.text.isdigit())
async def search_movie(message: types.Message):
    res_sub = await check_sub(message.from_user.id)
    if res_sub is not True and message.from_user.id != ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=n, url=u)] for n, u in res_sub])
        kb.inline_keyboard.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check")])
        return await message.answer("⚠️ Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=kb)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT file_id, caption, views FROM movies WHERE code = %s", (int(message.text),))
    movie = cur.fetchone()
    if movie:
        cur.execute("UPDATE movies SET views = views + 1 WHERE code = %s", (int(message.text),))
        conn.commit()
        await message.answer_video(video=movie[0], caption=f"🎬 {movie[1]}\n\n👁 Ko'rildi: {movie[2]+1}")
    else:
        await message.answer("❌ Bunday kodli kino topilmadi.")
    cur.close()
    conn.close()

# --- ADMIN FUNKSIYALAR (Kino Qo'shish) ---
@dp.message(F.text == "➕ Kino Qo'shish")
async def add_start(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Kino videosini yuboring:")
        await state.set_state(AdminStates.add_m_video)

@dp.message(AdminStates.add_m_video, F.video)
async def add_video(message: types.Message, state: FSMContext):
    await state.update_data(vid=message.video.file_id)
    await message.answer("Kino kodini kiriting:")
    await state.set_state(AdminStates.add_m_code)

@dp.message(AdminStates.add_m_code)
async def add_code(message: types.Message, state: FSMContext):
    await state.update_data(vcode=message.text)
    await message.answer("Kino nomini yozing:")
    await state.set_state(AdminStates.add_m_cap)

@dp.message(AdminStates.add_m_cap)
async def add_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO movies (code, file_id, caption) VALUES (%s, %s, %s)", 
                    (int(data['vcode']), data['vid'], message.text))
        conn.commit()
        await message.answer(f"✅ Saqlandi! Kod: {data['vcode']}")
    except:
        await message.answer("❌ Xato! Ehtimol bu kod bazada bor.")
    finally:
        cur.close()
        conn.close()
        await state.clear()

# --- ADMIN: KINO O'CHIRISH ---
@dp.message(F.text == "🗑 Kino O'chirish")
async def del_start(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("O'chirmoqchi bo'lgan kino kodini yozing:")
        await state.set_state(AdminStates.del_m_code)

@dp.message(AdminStates.del_m_code)
async def del_exec(message: types.Message, state: FSMContext):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM movies WHERE code = %s", (int(message.text),))
    conn.commit()
    cur.close()
    conn.close()
    await message.answer("✅ O'chirildi.")
    await state.clear()

# --- STATISTIKA ---
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    u = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM movies")
    m = cur.fetchone()[0]
    cur.close()
    conn.close()
    await message.answer(f"👤 Foydalanuvchilar: {u}\n🎬 Kinolar: {m}")

# --- REKLAMA ---
@dp.message(F.text == "✉️ Reklama Tarqatish")
async def ad_start(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Reklama postini yuboring:")
        await state.set_state(AdminStates.ad_msg)

@dp.message(AdminStates.ad_msg)
async def ad_msg(message: types.Message, state: FSMContext):
    await state.update_data(mid=message.message_id)
    await message.answer("Tugma (Nom + Link) yoki 'yo'q':")
    await state.set_state(AdminStates.ad_btn)

@dp.message(AdminStates.ad_btn)
async def ad_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    kb = None
    if " + " in message.text:
        n, u = message.text.split(" + ")
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=n, url=u)]])
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    
    s = 0
    for u in users:
        try:
            await bot.copy_message(u[0], ADMIN_ID, data['mid'], reply_markup=kb)
            s += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ {s} kishiga yuborildi.")
    await state.clear()

# --- ISHGA TUSHIRISH ---
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
