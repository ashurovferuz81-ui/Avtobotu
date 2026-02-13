import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F, MagicFilter
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

# --- SOZLAMALAR ---
API_TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA" # Yangilangan bo'lsa almashtiring
ADMIN_ID = 5775388579
DB_PATH = "/app/data/pro_kino.db" # Railway uchun. Kompyuterda bo'lsa "pro_kino.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- BAZA BILAN ISHLASH ---
def init_db():
    directory = os.path.dirname(DB_PATH)
    if directory and not os.path.exists(directory): os.makedirs(directory)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Kinolar jadvali (views - ko'rishlar soni)
    cur.execute("CREATE TABLE IF NOT EXISTS movies (code INTEGER PRIMARY KEY, file_id TEXT, caption TEXT, views INTEGER DEFAULT 0)")
    # Foydalanuvchilar jadvali
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    # Kanallar jadvali (Majburiy obuna uchun)
    cur.execute("CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY, url TEXT, chat_id TEXT)")
    conn.commit()
    conn.close()

def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    res = None
    if fetchone: res = cur.fetchone()
    if fetchall: res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- ADMIN HOLATLARI ---
class AdminState(StatesGroup):
    add_movie = State()
    add_channel_id = State()
    add_channel_url = State()

# --- TUGMALAR ---
def get_admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎬 Kino qo'shish"), KeyboardButton(text="🗑 Kino o'chirish")],
        [KeyboardButton(text="📢 Kanal qo'shish"), KeyboardButton(text="❌ Kanal o'chirish")],
        [KeyboardButton(text="📊 Statistika")]
    ], resize_keyboard=True)

# --- MAJBURIY OBUNA TEKSHIRUVI ---
async def check_sub(user_id):
    channels = execute_query("SELECT chat_id, url FROM channels", fetchall=True)
    not_subbed = []
    for chat_id, url in channels:
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                not_subbed.append(url)
        except Exception:
            not_subbed.append(url)
    return not_subbed

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def start(message: types.Message):
    # Foydalanuvchini bazaga qo'shish
    execute_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,), commit=True)
    
    if message.from_user.id == ADMIN_ID:
        await message.answer("Xush kelibsiz, Pro Admin!", reply_markup=get_admin_kb())
    else:
        await message.answer("Salom! Kino kodini yuboring.")

@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    user_count = execute_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
    movie_count = execute_query("SELECT COUNT(*) FROM movies", fetchone=True)[0]
    total_views = execute_query("SELECT SUM(views) FROM movies", fetchone=True)[0] or 0
    
    text = (f"📊 <b>Bot Statistikasi:</b>\n\n"
            f"👤 Foydalanuvchilar: {user_count} ta\n"
            f"🎬 Kinolar soni: {movie_count} ta\n"
            f"👁 Jami ko'rishlar: {total_views} marta")
    await message.answer(text, parse_mode="HTML")

# --- KINO BOSHQARUVI ---
@dp.message(F.text == "🎬 Kino qo'shish")
async def start_add_movie(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Kino videosini yuboring (caption bilan):")
        await state.set_state(AdminState.add_movie)

@dp.message(AdminState.add_movie, F.video)
async def save_movie(message: types.Message, state: FSMContext):
    res = execute_query("SELECT MAX(code) FROM movies", fetchone=True)
    new_code = 101 if res[0] is None else res[0] + 1
    execute_query("INSERT INTO movies (code, file_id, caption) VALUES (?, ?, ?)", 
                  (new_code, message.video.file_id, message.caption or "Kino"), commit=True)
    await message.answer(f"✅ Saqlandi! Kod: <code>{new_code}</code>", parse_mode="HTML")
    await state.clear()

# --- KANAL BOSHQARUVI ---
@dp.message(F.text == "📢 Kanal qo'shish")
async def start_add_chan(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Kanal ID raqamini yuboring (Masalan: -100...):")
        await state.set_state(AdminState.add_channel_id)

@dp.message(AdminState.add_channel_id)
async def save_chan_id(message: types.Message, state: FSMContext):
    await state.update_data(chat_id=message.text)
    await message.answer("Kanal linkini yuboring (Masalan: https://t.me/...):")
    await state.set_state(AdminState.add_channel_url)

@dp.message(AdminState.add_channel_url)
async def save_chan_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    execute_query("INSERT INTO channels (chat_id, url) VALUES (?, ?)", (data['chat_id'], message.text), commit=True)
    await message.answer("✅ Kanal qo'shildi!")
    await state.clear()

# --- FOYDALANUVCHI KINO QIDIRISH ---
@dp.message(F.text.regexp(r'^\d+$')) # Faqat raqam bo'lsa
async def get_movie(message: types.Message):
    # Majburiy obuna tekshiruvi
    not_subbed = await check_sub(message.from_user.id)
    if not_subbed:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Obuna bo'lish", url=u)] for u in not_subbed])
        return await message.answer("Botingiz ishlashi uchun kanallarga obuna bo'ling:", reply_markup=kb)

    code = int(message.text)
    movie = execute_query("SELECT file_id, caption, views FROM movies WHERE code = ?", (code,), fetchone=True)
    
    if movie:
        file_id, caption, views = movie
        new_views = views + 1
        execute_query("UPDATE movies SET views = ? WHERE code = ?", (new_views, code), commit=True)
        await message.answer_video(video=file_id, caption=f"{caption}\n\n👁 Ko'rildi: {new_views}")
    else:
        await message.answer("❌ Kino topilmadi.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
