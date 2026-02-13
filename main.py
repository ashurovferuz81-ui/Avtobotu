import asyncio
import logging
import os
import psycopg2
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
DB_URL = os.getenv("DATABASE_URL") # Railway avtomatik ulaydi

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- POSTGRESQL FUNKSIYALARI ---
def get_db_connection():
    # Railway-da sslmode=require shart
    return psycopg2.connect(DB_URL, sslmode='require')

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS movies (
        code INTEGER PRIMARY KEY, 
        file_id TEXT, 
        caption TEXT, 
        views INTEGER DEFAULT 0)""")
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, joined_date DATE)")
    cur.execute("CREATE TABLE IF NOT EXISTS channels (id SERIAL PRIMARY KEY, chat_id TEXT, url TEXT, name TEXT)")
    conn.commit()
    cur.close()
    conn.close()

# --- HOLATLAR ---
class Form(StatesGroup):
    add_vid = State()
    add_code = State()
    add_cap = State()
    del_code = State()
    ad_msg = State()
    ad_btn = State()
    ch_id = State()
    ch_url = State()
    ch_name = State()

# --- KLAVIATURA ---
def admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Kino Qo'shish"), KeyboardButton(text="🗑 Kino O'chirish")],
        [KeyboardButton(text="📢 Kanal Sozlamalari"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="✉️ Reklama Tarqatish")]
    ], resize_keyboard=True)

# --- OBUNA TEKSHIRISH ---
async def is_subbed(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT chat_id, url, name FROM channels")
    chans = cur.fetchall()
    cur.close()
    conn.close()
    
    if not chans: return True
    not_sub = []
    for cid, url, name in chans:
        try:
            m = await bot.get_chat_member(chat_id=cid, user_id=user_id)
            if m.status in ["left", "kicked"]: not_sub.append((name, url))
        except: not_sub.append((name, url))
    return not_sub if not_sub else True

# --- ASOSIY HANDLERLAR ---

@dp.message(Command("start"))
async def start(message: types.Message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id, joined_date) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING", 
                (message.from_user.id, datetime.now().date()))
    conn.commit()
    cur.close()
    conn.close()
    
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 <b>Admin Panel (PostgreSQL)</b>", reply_markup=admin_kb(), parse_mode="HTML")
    else:
        await message.answer("🍿 <b>Kino kodini yuboring:</b>", parse_mode="HTML")

@dp.message(F.text.isdigit())
async def search(message: types.Message):
    res = await is_subbed(message.from_user.id)
    if res is not True and message.from_user.id != ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=n, url=u)] for n, u in res])
        kb.inline_keyboard.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="recheck")])
        return await message.answer("❌ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>", reply_markup=kb, parse_mode="HTML")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT file_id, caption, views FROM movies WHERE code = %s", (int(message.text),))
    m = cur.fetchone()
    if m:
        cur.execute("UPDATE movies SET views = views + 1 WHERE code = %s", (int(message.text),))
        conn.commit()
        await message.answer_video(video=m[0], caption=f"🎬 <b>{m[1]}</b>\n\n👁 Ko'rildi: {m[2]+1}", parse_mode="HTML")
    else:
        await message.answer("😔 <b>Kino topilmadi.</b>", parse_mode="HTML")
    cur.close()
    conn.close()

@dp.callback_query(F.data == "recheck")
async def recheck(call: CallbackQuery):
    if await is_subbed(call.from_user.id) is True:
        await call.message.edit_text("✅ Rahmat! Endi kodni yuboring.")
    else:
        await call.answer("❌ Hali hamma kanallarga a'zo emassiz!", show_alert=True)

# --- ADMIN: KINO QO'SHISH ---
@dp.message(F.text == "➕ Kino Qo'shish")
async def add_k(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Videoni yuboring:")
        await state.set_state(Form.add_vid)

@dp.message(Form.add_vid, F.video)
async def add_v(message: types.Message, state: FSMContext):
    await state.update_data(vid=message.video.file_id)
    await message.answer("Kino uchun kod kiriting:")
    await state.set_state(Form.add_code)

@dp.message(Form.add_code)
async def add_c(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text)
    await message.answer("Kino nomini yozing:")
    await state.set_state(Form.add_cap)

@dp.message(Form.add_cap)
async def add_f(message: types.Message, state: FSMContext):
    d = await state.get_data()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO movies (code, file_id, caption) VALUES (%s, %s, %s)", 
                    (int(d['code']), d['vid'], message.text))
        conn.commit()
        await message.answer(f"✅ Saqlandi! Kod: {d['code']}")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")
    finally:
        cur.close()
        conn.close()
        await state.clear()

# --- ADMIN: KINO O'CHIRISH ---
@dp.message(F.text == "🗑 Kino O'chirish")
async def del_k(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("O'chirmoqchi bo'lgan kino kodini yozing:")
        await state.set_state(Form.del_code)

@dp.message(Form.del_code)
async def del_v(message: types.Message, state: FSMContext):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM movies WHERE code = %s", (int(message.text),))
    conn.commit()
    cur.close()
    conn.close()
    await message.answer(f"✅ {message.text} o'chirildi.")
    await state.clear()

# --- ADMIN: REKLAMA ---
@dp.message(F.text == "✉️ Reklama Tarqatish")
async def ad_1(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Reklama postini yuboring:")
        await state.set_state(Form.ad_msg)

@dp.message(Form.ad_msg)
async def ad_2(message: types.Message, state: FSMContext):
    await state.update_data(mid=message.message_id)
    await message.answer("Tugma: `Nom + Link` (masalan: `Kanal + https://t.me/...`) yoki `yo'q` deb yozing.")
    await state.set_state(Form.ad_btn)

@dp.message(Form.ad_btn)
async def ad_3(message: types.Message, state: FSMContext):
    d = await state.get_data()
    kb = None
    if " + " in message.text:
        n, u = message.text.split(" + ")
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=n, url=u)]])
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    us = cur.fetchall()
    cur.close()
    conn.close()
    
    s = 0
    await message.answer("🚀 Tarqatilmoqda...")
    for u in us:
        try:
            await bot.copy_message(u[0], ADMIN_ID, d['mid'], reply_markup=kb)
            s += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ {s} kishiga yuborildi.")
    await state.clear()

# --- KANAL SOZLAMALARI ---
@dp.message(F.text == "📢 Kanal Sozlamalari")
async def ch_m(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM channels")
        chs = cur.fetchall()
        cur.close()
        conn.close()
        
        txt = "<b>Kanallar:</b>\n\n" + "\n".join([f"{n}" for i, n in chs])
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Qo'shish", callback_data="add_ch")],
            [InlineKeyboardButton(text="🗑 Tozalash", callback_data="clear_ch")]
        ])
        await message.answer(txt, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "add_ch")
async def ch_a(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Kanal ID (-100...):")
    await state.set_state(Form.ch_id)

@dp.message(Form.ch_id)
async def ch_i(message: types.Message, state: FSMContext):
    await state.update_data(chid=message.text)
    await message.answer("Kanal Link (https://...):")
    await state.set_state(Form.ch_url)

@dp.message(Form.ch_url)
async def ch_u(message: types.Message, state: FSMContext):
    await state.update_data(churl=message.text)
    await message.answer("Tugma nomi:")
    await state.set_state(Form.ch_name)

@dp.message(Form.ch_name)
async def ch_f(message: types.Message, state: FSMContext):
    d = await state.get_data()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO channels (chat_id, url, name) VALUES (%s, %s, %s)", (d['chid'], d['churl'], message.text))
    conn.commit()
    cur.close()
    conn.close()
    await message.answer("✅ Kanal qo'shildi!")
    await state.clear()

# --- STATISTIKA ---
@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    u = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM movies")
    m = cur.fetchone()[0]
    cur.close()
    conn.close()
    await message.answer(f"👤 A'zolar: {u}\n🎬 Kinolar: {m}")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
