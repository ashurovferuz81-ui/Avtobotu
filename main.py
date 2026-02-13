import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
# Tokenni Railway Environment Variable-ga yozamiz (xavfsizlik uchun)
# Yoki shu yerga qo'shtirnoq ichida yozing: "TOKEN"
API_TOKEN = os.getenv("BOT_TOKEN") 
ADMIN_ID = 5775388579  # Sizning ID raqamingiz

# Ma'lumotlar bazasi fayli (Railway Volume uchun muhim)
DB_NAME = "/app/data/kino.db" # Agar Railway Volume ishlatsangiz "/app/data/" bo'lishi kerak. Oddiy kompyuterda shunchaki "kino.db"

# Loglarni yoqish
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- BAZA BILAN ISHLASH (SQLITE) ---
def db_connect():
    # Papka borligini tekshirish (Railway uchun)
    directory = os.path.dirname(DB_NAME)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            code INTEGER PRIMARY KEY,
            file_id TEXT NOT NULL,
            caption TEXT
        )
    """)
    conn.commit()
    return conn

# --- ADMIN PANEL UCHUN HOLATLAR ---
class AdminState(StatesGroup):
    waiting_for_video = State()
    waiting_for_delete_code = State()

# --- TUGMALAR ---
admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎬 Kino qo'shish"), KeyboardButton(text="🗑 Kino o'chirish")],
        [KeyboardButton(text="📊 Statistika")]
    ],
    resize_keyboard=True
)

# --- START BUYRUG'I ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"Salom Admin! Xush kelibsiz.", reply_markup=admin_kb)
    else:
        await message.answer("Salom! Menga kino kodini yuboring.")

# --- ADMIN: KINO QO'SHISH ---
@dp.message(F.text == "🎬 Kino qo'shish")
async def ask_video(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Kinoni (videoni) menga yuboring:")
        await state.set_state(AdminState.waiting_for_video)

@dp.message(AdminState.waiting_for_video, F.video)
async def save_video(message: types.Message, state: FSMContext):
    file_id = message.video.file_id
    caption = message.caption or "Kino"
    
    conn = db_connect()
    cursor = conn.cursor()
    
    # Avtomatik kod yaratish (eng oxirgi kod + 1)
    cursor.execute("SELECT MAX(code) FROM movies")
    result = cursor.fetchone()
    new_code = 101 if result[0] is None else result[0] + 1
    
    cursor.execute("INSERT INTO movies (code, file_id, caption) VALUES (?, ?, ?)", (new_code, file_id, caption))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ Kino saqlandi!\n\n🔑 <b>Kino kodi:</b> {new_code}", parse_mode="HTML")
    await state.clear()

# --- ADMIN: KINO O'CHIRISH ---
@dp.message(F.text == "🗑 Kino o'chirish")
async def ask_delete_code(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("O'chirmoqchi bo'lgan kino kodini yozing:")
        await state.set_state(AdminState.waiting_for_delete_code)

@dp.message(AdminState.waiting_for_delete_code)
async def delete_movie(message: types.Message, state: FSMContext):
    try:
        code = int(message.text)
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
        if cursor.rowcount > 0:
            await message.answer(f"✅ {code}-kodli kino o'chirildi.")
        else:
            await message.answer("❌ Bunday kod topilmadi.")
        conn.commit()
        conn.close()
    except ValueError:
        await message.answer("Iltimos, faqat raqam yuboring.")
    
    await state.clear()

# --- ADMIN: STATISTIKA ---
@dp.message(F.text == "📊 Statistika")
async def show_stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies")
        count = cursor.fetchone()[0]
        conn.close()
        await message.answer(f"Botda jami <b>{count}</b> ta kino bor.", parse_mode="HTML")

# --- FOYDALANUVCHI: KINO IZLASH ---
@dp.message()
async def get_movie(message: types.Message):
    # Agar admin panelda bo'lsa va noto'g'ri narsa yozsa
    if message.text and message.text.startswith("/"):
        return

    try:
        code = int(message.text)
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, caption FROM movies WHERE code = ?", (code,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            file_id, caption = result
            await message.answer_video(video=file_id, caption=f"🍿 {caption}\n\n🤖 @{ (await bot.get_me()).username }")
        else:
            await message.answer("😔 Bunday kodli kino topilmadi.")
    except ValueError:
        await message.answer("Kino kodini raqamda yuboring (masalan: 101)")

# --- ISHGA TUSHIRISH ---
async def main():
    # Bazani yaratish
    db_connect()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
