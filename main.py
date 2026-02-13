import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                            InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery)

# --- SOZLAMALAR ---
API_TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579
DB_PATH = "/app/data/final_kino.db" # Railway Volume

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- DATABASE ---
def db_init():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS movies (code INTEGER PRIMARY KEY, file_id TEXT, caption TEXT, views INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, url TEXT)")
    conn.commit()
    conn.close()

def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    res = None
    if fetchone: res = cur.fetchone()
    if fetchall: res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- STATES ---
class AdminStates(StatesGroup):
    # Kino qo'shish
    waiting_for_movie_video = State()
    waiting_for_movie_code = State()
    # Reklama
    waiting_for_ad_content = State()
    waiting_for_ad_button = State()
    # Kanal
    waiting_for_chan_id = State()
    waiting_for_chan_url = State()

# --- KEYBOARDS ---
def admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎬 Kino qo'shish"), KeyboardButton(text="🗑 Kino o'chirish")],
        [KeyboardButton(text="📢 Kanal qo'shish"), KeyboardButton(text="❌ Kanal o'chirish")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="✉️ Tugmali Reklama")],
    ], resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    db_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,), commit=True)
    if message.from_user.id == ADMIN_ID:
        await message.answer("Boshqaruv paneli:", reply_markup=admin_menu())
    else:
        await message.answer("Xush kelibsiz! Kino kodini yuboring.")

# --- KINO QO'SHISH (MANUAL CODE) ---
@dp.message(F.text == "🎬 Kino qo'shish")
async def add_m_start(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Kino videosini yuboring:")
        await state.set_state(AdminStates.waiting_for_movie_video)

@dp.message(AdminStates.waiting_for_movie_video, F.video)
async def add_m_video(message: types.Message, state: FSMContext):
    await state.update_data(vid=message.video.file_id, cap=message.caption or "Kino")
    await message.answer("Ushbu kino uchun KOD kiriting (faqat raqam):")
    await state.set_state(AdminStates.waiting_for_movie_code)

@dp.message(AdminStates.waiting_for_movie_code)
async def add_m_code(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Kod faqat raqam bo'lsin!")
    
    code = int(message.text)
    data = await state.get_data()
    
    try:
        db_query("INSERT INTO movies (code, file_id, caption) VALUES (?, ?, ?)", 
                 (code, data['vid'], data['cap']), commit=True)
        await message.answer(f"✅ Kino saqlandi!\nKod: {code}")
        await state.clear()
    except sqlite3.IntegrityError:
        await message.answer("❌ Bu kod bazada bor! Boshqa kod yozing:")

# --- TUGMALI REKLAMA ---
@dp.message(F.text == "✉️ Tugmali Reklama")
async def ad_start(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Reklama xabarini yuboring (Rasm, Video yoki Matn):")
        await state.set_state(AdminStates.waiting_for_ad_content)

@dp.message(AdminStates.waiting_for_ad_content)
async def ad_content(message: types.Message, state: FSMContext):
    await state.update_data(msg_id=message.message_id)
    await message.answer("Tugma uchun link va nomni quyidagi formatda yuboring:\n\n`Nom + Link` (masalan: `Kanalimiz + https://t.me/...`)", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_ad_button)

@dp.message(AdminStates.waiting_for_ad_button)
async def ad_send(message: types.Message, state: FSMContext):
    try:
        btn_name, btn_url = message.text.split(" + ")
        data = await state.get_data()
        users = db_query("SELECT user_id FROM users", fetchall=True)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_name, url=btn_url)]])
        
        count = 0
        for user in users:
            try:
                await bot.copy_message(chat_id=user[0], from_chat_id=ADMIN_ID, message_id=data['msg_id'], reply_markup=kb)
                count += 1
                await asyncio.sleep(0.05)
            except: pass
        
        await message.answer(f"✅ Reklama {count} kishiga yuborildi.")
        await state.clear()
    except:
        await message.answer("Format xato! Qaytadan yuboring (Nom + Link):")

# --- KINO QIDIRISH ---
@dp.message(F.text.isdigit())
async def search(message: types.Message):
    # Obuna tekshiruvi
    chans = db_query("SELECT chat_id, url FROM channels", fetchall=True)
    not_sub = []
    for cid, url in chans:
        try:
            m = await bot.get_chat_member(cid, message.from_user.id)
            if m.status in ['left', 'kicked']: not_sub.append(url)
        except: not_sub.append(url)

    if not_sub:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Obuna bo'lish", url=u)] for u in not_sub])
        return await message.answer("Kino ko'rish uchun kanallarga a'zo bo'ling:", reply_markup=kb)

    res = db_query("SELECT file_id, caption, views FROM movies WHERE code = ?", (int(message.text),), fetchone=True)
    if res:
        db_query("UPDATE movies SET views = views + 1 WHERE code = ?", (int(message.text),), commit=True)
        await message.answer_video(video=res[0], caption=f"{res[1]}\n\n👁 Ko'rildi: {res[2]+1}")
    else:
        await message.answer("Kino topilmadi.")

# --- QOLGAN FUNKSIYALAR (Kanal qo'shish/Statistika) ---
@dp.message(F.text == "📊 Statistika")
async def st(message: types.Message):
    u = db_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
    m = db_query("SELECT COUNT(*) FROM movies", fetchone=True)[0]
    v = db_query("SELECT SUM(views) FROM movies", fetchone=True)[0] or 0
    await message.answer(f"👤 Foydalanuvchilar: {u}\n🎬 Kinolar: {m}\n👁 Jami ko'rishlar: {v}")

@dp.message(F.text == "📢 Kanal qo'shish")
async def ch_add(message: types.Message, state: FSMContext):
    await message.answer("Kanal ID yuboring (-100...):")
    await state.set_state(AdminStates.waiting_for_chan_id)

@dp.message(AdminStates.waiting_for_chan_id)
async def ch_id(message: types.Message, state: FSMContext):
    await state.update_data(ci=message.text)
    await message.answer("Kanal Linkini yuboring:")
    await state.set_state(AdminStates.waiting_for_chan_url)

@dp.message(AdminStates.waiting_for_chan_url)
async def ch_url(message: types.Message, state: FSMContext):
    d = await state.get_data()
    db_query("INSERT INTO channels (chat_id, url) VALUES (?, ?)", (d['ci'], message.text), commit=True)
    await message.answer("Kanal qo'shildi!")
    await state.clear()

async def main():
    db_init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
