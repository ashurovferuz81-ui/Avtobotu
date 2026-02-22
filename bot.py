 import os
import sqlite3
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
import yt_dlp

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
CHANNELS = ["@Sardorbeko008"]  # Majburiy obuna kanali (username bilan)

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- DATABASE ---
conn = sqlite3.connect("downloader_bot.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
conn.commit()

# --- FUNKSIYALAR ---
async def check_sub(user_id):
    """Obunani tekshirish"""
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            continue
    return True

def download_video(url):
    """Videoni yuklash"""
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'video_%(id)s.mp4',
        'max_filesize': 45 * 1024 * 1024,
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# --- KEYBOARDS ---
def sub_kb():
    kb = []
    for ch in CHANNELS:
        kb.append([InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{ch[1:]}")])
    kb.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_subs")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Reklama yuborish")]
    ], resize_keyboard=True)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (m.from_user.id,))
    conn.commit()
    
    if await check_sub(m.from_user.id):
        text = f"Salom {m.from_user.first_name}! Link yuboring, videoni yuklab beraman."
        kb = admin_kb() if m.from_user.id == ADMIN_ID else None
        await m.answer(text, reply_markup=kb)
    else:
        await m.answer("❌ Botdan foydalanish uchun kanalimizga obuna bo'ling!", reply_markup=sub_kb())

@dp.callback_query(F.data == "check_subs")
async def check_btn(c: types.CallbackQuery):
    if await check_sub(c.from_user.id):
        await c.message.edit_text("✅ Raxmat! Endi link yuborishingiz mumkin.")
    else:
        await c.answer("❌ Hali obuna bo'lmagansiz!", show_alert=True)

# Admin Panel: Statistika
@dp.message(F.text == "📊 Statistika", F.from_user.id == ADMIN_ID)
async def stats(m: types.Message):
    count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    await m.answer(f"👥 Botdagi jami foydalanuvchilar: {count} ta")

# Linklarni qayta ishlash
@dp.message(F.text.contains("http"))
async def handle_video(m: types.Message):
    if not await check_sub(m.from_user.id):
        return await m.answer("Avval obuna bo'ling!", reply_markup=sub_kb())
    
    msg = await m.answer("⏳ Video tayyorlanmoqda...")
    try:
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_video, m.text)
        
        video = types.FSInputFile(file_path)
        await m.answer_video(video, caption="✅ Yuklab olindi!\nBot: @sizning_botingiz")
        os.remove(file_path)
        await msg.delete()
    except Exception as e:
        await msg.edit_text("❌ Xatolik! Link noto'g'ri yoki video hajmi juda katta (limit 50MB).")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
