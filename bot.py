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
CHANNELS = ["@Sardorbeko008"]

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- DATABASE ---
conn = sqlite3.connect("downloader_pro.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
conn.commit()

# --- YUKLASH FUNKSIYASI ---
def download_media(url, mode="video"):
    """
    Instagram, TikTok va YouTubedan video/audio yuklash.
    """
    unique_id = str(asyncio.get_event_loop().time()).replace(".", "")
    
    if mode == "video":
        opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'video_{unique_id}.mp4',
            'max_filesize': 49 * 1024 * 1024, # 50MB Telegram limiti
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4'
        }
    else: # Musiqa rejimi
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'audio_{unique_id}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if mode == "audio":
            return filename.rsplit('.', 1)[0] + ".mp3"
        return filename

async def check_sub(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ["left", "kicked"]: return False
        except: continue
    return True

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (m.from_user.id,))
    conn.commit()
    
    if await check_sub(m.from_user.id):
        kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Reklama")]
        ], resize_keyboard=True) if m.from_user.id == ADMIN_ID else None
        await m.answer("👋 Instagram, TikTok yoki YouTube linkini yuboring!", reply_markup=kb)
    else:
        btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{CHANNELS[0][1:]}")],
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="recheck")]
        ])
        await m.answer("❌ Botdan foydalanish uchun kanalga a'zo bo'ling!", reply_markup=btn)

@dp.message(F.text.contains("http"))
async def link_handler(m: types.Message):
    if not await check_sub(m.from_user.id):
        return await m.answer("Avval obuna bo'ling!")
    
    url = m.text
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Video", callback_data=f"v|{url}"),
         InlineKeyboardButton(text="🎵 Musiqa (MP3)", callback_data=f"a|{url}")]
    ])
    await m.answer("Nima yuklaymiz?", reply_markup=kb)

@dp.callback_query(F.data.startswith(("v|", "a|")))
async def dl_callback(c: types.CallbackQuery):
    data = c.data.split("|")
    mode = "video" if data[0] == "v" else "audio"
    url = data[1]
    
    msg = await c.message.answer(f"⏳ Yuklanmoqda...")
    await c.answer()
    
    try:
        loop = asyncio.get_event_loop()
        path = await loop.run_in_executor(None, download_media, url, mode)
        
        if os.path.exists(path):
            file = types.FSInputFile(path)
            if mode == "video":
                await c.message.answer_video(file, caption="✅ @sizning_botingiz")
            else:
                await c.message.answer_audio(file, caption="✅ @sizning_botingiz")
            os.remove(path)
            await msg.delete()
        else:
            raise Exception("Fayl yuklanmadi")
            
    except Exception as e:
        logging.error(e)
        await msg.edit_text("❌ Xatolik! Sabablar:\n1. Link noto'g'ri.\n2. Fayl 50 MB dan katta.\n3. Bu video shaxsiy (private).")

# Reklama yuborish (Admin uchun)
@dp.message(F.text == "📢 Reklama", F.from_user.id == ADMIN_ID)
async def start_ads(m: types.Message):
    await m.answer("Reklama xabarini yuboring (rasm, matn yoki video):")

@dp.message(F.from_user.id == ADMIN_ID)
async def send_ads(m: types.Message):
    if m.text in ["📊 Statistika", "📢 Reklama"]: return
    
    users = cur.execute("SELECT id FROM users").fetchall()
    count = 0
    for user in users:
        try:
            await m.copy_to(user[0])
            count += 1
            await asyncio.sleep(0.05) # Bloklanib qolmaslik uchun
        except: continue
    await m.answer(f"✅ Reklama {count} ta foydalanuvchiga yuborildi.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
