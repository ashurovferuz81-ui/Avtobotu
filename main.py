import sqlite3
import random
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# --- SOZLAMALAR ---
TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579  # O'zingizning Telegram ID raqamingizni yozing (Masalan: @userinfobot orqali bilsangiz bo'ladi)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- BAZA BILAN ISHLASH ---
db = sqlite3.connect("konkurs.db")
cursor = db.cursor()

# Jadvallarni yaratish
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS channels (url TEXT PRIMARY KEY)")
db.commit()

# --- YORDAMCHI FUNKSIYALAR ---
async def check_sub(user_id):
    """Barcha majburiy kanallarga a'zolikni tekshirish"""
    cursor.execute("SELECT url FROM channels")
    channels = cursor.fetchall()
    for (channel,) in channels:
        try:
            # Username orqali tekshirish (@ belgisidan foydalanamiz)
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            # Agar bot kanalga admin bo'lmasa yoki kanal topilmasa
            return False
    return True

# --- FOYDALANUVCHI QISMI ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    cursor.execute("SELECT url FROM channels")
    channels = cursor.fetchall()
    
    if not channels:
        await message.answer("Hozircha faol konkurslar yo'q.")
        return

    builder = InlineKeyboardBuilder()
    for (channel,) in channels:
        # Linkni foydalanuvchiga chiroyli ko'rsatish (https://t.me/...)
        link = f"https://t.me/{channel.replace('@', '')}"
        builder.row(types.InlineKeyboardButton(text="Kanalga a'zo bo'lish", url=link))
    
    builder.row(types.InlineKeyboardButton(text="✅ Qatnashish", callback_data="check_sub"))
    
    await message.answer(
        "Konkursda qatnashish uchun kanallarga a'zo bo'ling va pastdagi tugmani bosing:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "check_sub")
async def check_callback(call: types.CallbackQuery):
    is_member = await check_sub(call.from_user.id)
    if is_member:
        try:
            cursor.execute("INSERT INTO users (user_id) VALUES (?)", (call.from_user.id,))
            db.commit()
            await call.message.edit_text("✅ Siz ro'yxatga olindingiz! G'oliblar tez orada aniqlanadi.")
        except sqlite3.IntegrityError:
            await call.answer("Siz allaqachon ro'yxatdan o'tgansiz!", show_alert=True)
    else:
        await call.answer("Barcha kanallarga a'zo bo'lishingiz shart!", show_alert=True)

# --- ADMIN PANEL QISMI ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    text = (
        "💻 **Admin Panel**\n\n"
        "/add_chan @username - Kanal qo'shish\n"
        "/del_chan @username - Kanalni o'chirish\n"
        "/channels - Kanallar ro'yxati\n"
        "/winner - G'olibni aniqlash\n"
        "/send XABAR - Barcha foydalanuvchilarga SMS yuborish\n"
        "/count - Qatnashchilar soni"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("add_chan"))
async def add_channel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        channel = message.text.split()[1]
        if not channel.startswith("@"):
            await message.answer("Xatolik! Kanalni @username shaklida yuboring.")
            return
        cursor.execute("INSERT INTO channels (url) VALUES (?)", (channel,))
        db.commit()
        await message.answer(f"Kanal qo'shildi: {channel}")
    except:
        await message.answer("Xatolik yoki kanal allaqachon bor.")

@dp.message(Command("winner"))
async def pick_winner(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    if users:
        winner_id = random.choice(users)[0]
        await message.answer(f"🎉 G'olib aniqlandi! ID: {winner_id}\nProfil: [Havola](tg://user?id={winner_id})", parse_mode="Markdown")
    else:
        await message.answer("Hali qatnashchilar yo'q.")

@dp.message(Command("send"))
async def send_ads(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/send ", "")
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    count = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, text)
            count += 1
        except: pass
    await message.answer(f"Xabar {count} ta foydalanuvchiga yuborildi.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
