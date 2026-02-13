import asyncio
import os
import sqlite3
import logging
from groq import Groq
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                            InlineKeyboardMarkup, InlineKeyboardButton)

# --- KONFIGURATSIYA ---
API_TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579
# API kalitni to'g'ridan-to'g'ri kodga qo'ydim:
GROQ_API_KEY = "Gsk_84rl0SgB7ZLUlTrCDCDZWGdyb3FYzlglPBgNksvZCmODrbL81KOO" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

# --- SQLITE BAZA ---
def db_init():
    # Railway-da sqlite3 ishlashi uchun bazani yaratamiz
    conn = sqlite3.connect("quran_ai.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS lessons (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, file_id TEXT)")
    conn.commit()
    conn.close()

# --- TUGMALAR ---
def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🎤 Qiroatni tekshirish (AI)")],
        [KeyboardButton(text="📖 Qur'on darslari"), KeyboardButton(text="📊 Statistika")]
    ], resize_keyboard=True)

# --- AI TAHLIL FUNKSIYASI ---
async def analyze_voice_free(file_path):
    try:
        # 1. Ovozni Whisper orqali matnga o'girish
        with open(file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(file_path, file.read()),
                model="whisper-large-v3",
                language="ar"
            )
        user_text = transcription.text

        # 2. Tajvid tahlili (Llama-3 modelida)
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "Sen Qur'on va tajvid ustozisan. Foydalanuvchi o'qigan matnni tahlil qil va xatolarni o'zbek tilida juda muloyimlik bilan tushuntir."},
                {"role": "user", "content": f"Foydalanuvchi quyidagicha o'qidi: {user_text}. Tajvid xatolarini tushuntir."}
            ]
        )
        return user_text, completion.choices[0].message.content
    except Exception as e:
        return None, str(e)

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def start(message: types.Message):
    conn = sqlite3.connect("quran_ai.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    
    await message.answer(
        "🕋 Assalomu alaykum! Qur'on va Tajvid AI botiga xush kelibsiz.\n\n"
        "Men ovozingizni eshitib, xatolaringizni aytib beraman. Marhamat, ovozli xabar (voice) yuboring.",
        reply_markup=main_kb()
    )

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    status_msg = await message.answer("🎧 Ovozingiz tahlil qilinmoqda, iltimos kuting...")
    
    # Ovozni yuklab olish
    file_info = await bot.get_file(message.voice.file_id)
    file_path = f"{message.voice.file_id}.ogg"
    await bot.download_file(file_info.file_path, file_path)
    
    # AI orqali tahlil qilish
    text, feedback = await analyze_voice_free(file_path)
    
    if text:
        await status_msg.edit_text(
            f"📖 **Siz o'qigan matn:**\n`{text}`\n\n"
            f"📝 **AI Tajvid Ustoz tavsiyasi:**\n{feedback}",
            parse_mode="Markdown"
        )
    else:
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {feedback}")
    
    # Faylni tozalash
    if os.path.exists(file_path):
        os.remove(file_path)

@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):
    conn = sqlite3.connect("quran_ai.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    await message.answer(f"👤 Bot a'zolari soni: {count} ta")

async def main():
    db_init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
