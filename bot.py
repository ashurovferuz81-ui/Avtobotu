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
CHANNELS = ["@Sardorbeko008"] # Kanalingiz username'i

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- DATABASE ---
conn = sqlite3.connect("downloader_pro.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
conn.commit()

# --- YUKLASH FUNKSIYALARI ---
def download_media(url, mode="video"):
    """Video yoki Audio yuklash funksiyasi"""
    if mode == "video":
        opts = {
            'format': 'best',
            'outtmpl': 'file_%(id)s.mp4',
            'max_filesize': 48 * 1024 * 1024,
            'quiet': True
        }
    else: # audio rejim
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'file_%(id)s.mp3',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")

async def check_sub(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ["left", "kicked"]: return False
        except: continue
    return True

# --- KEYBOARDS ---
def get_mode_kb(url):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Video yuklash", callback_data=f"vid|{url}")],
        [InlineKeyboardButton(text="🎵 Musiqasini (MP3) yuklash", callback_data=f"aud|{url}")]
    ])

def admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Reklama")]
    ], resize_keyboard=True)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (m.from_user.id,))
    conn.commit()
    
    if await check_sub(m.from_user.id):
        kb = admin_kb() if m.from_user.id == ADMIN_ID else None
        await m.answer("👋 Link yuboring, men uni Video yoki MP3 qilib beraman!", reply_markup=kb)
    else:
        btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{CHANNELS[0][1:]}")],
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="recheck")]
        ])
        await m.answer("❌ Botdan foydalanish uchun kanalga a'zo bo'ling!", reply_markup=btn)

@dp.message(F.text.contains("http"))
async def handle_link(m: types.Message):
    if not await check_sub(m.from_user.id):
        return await m.answer("Avval obuna bo'ling!")
    
    await m.answer("Tanlang, qaysi formatda yuklaymiz?", reply_markup=get_mode_kb(m.text))

@dp.callback_query(F.data.startswith(("vid|", "aud|")))
async def process_download(c: types.CallbackQuery):
    mode_code, url = c.data.split("|")
    mode = "video" if mode_code == "vid" else "audio"
    
    await c.message.edit_text(f"⏳ {mode.capitalize()} tayyorlanmoqda...")
    
    try:
        loop = asyncio.get_event_loop()
        path = await loop.run_in_executor(None, download_media, url, mode)
        
        file = types.FSInputFile(path)
        if mode == "video":
            await c.message.answer_video(file, caption="✅ Video tayyor!")
        else:
            await c.message.answer_audio(file, caption="✅ Musiqa tayyor!")
            
        os.remove(path)
        await c.message.delete()
    except Exception as e:
        await c.message.edit_text("❌ Xatolik! Link noto'g'ri yoki fayl juda katta.")

@dp.message(F.text == "📊 Statistika", F.from_user.id == ADMIN_ID)
async def stats(m: types.Message):
    count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    await m.answer(f"👥 Bot a'zolari: {count} ta")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
