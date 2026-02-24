import sqlite3
import requests
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = '8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU'
WEATHER_API = 'a488ffc4473fa950a0c76d19b0bad387'
ADMIN_ID = 5775388579

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- FSM (Holatlarni saqlash uchun) ---
class AdminStates(StatesGroup):
    waiting_for_ads = State()
    waiting_for_channel = State()
    waiting_for_photo_region = State()
    waiting_for_photo = State()

# --- SQLITE BAZA ---
def init_db():
    conn = sqlite3.connect("bot_base.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS region_photos (region TEXT PRIMARY KEY, photo_id TEXT)")
    conn.commit()
    conn.close()

# --- ADMIN INLINE KLAVIATURASI ---
def admin_inline_kb():
    kb = [
        [InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_send_ads")],
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admin_add_ch"),
         InlineKeyboardButton(text="❌ Kanal o'chirish", callback_data="admin_del_ch")],
        [InlineKeyboardButton(text="🖼 Viloyat rasmini qo'yish", callback_data="admin_set_photo")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stat")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ASOSIY MENULAR (Viloyatlar) ---
REGIONS = {
    "Toshkent": ["Toshkent sh.", "Chirchiq", "Angren", "Olmaliq"],
    "Buxoro": ["Buxoro sh.", "Vobkent", "Romitan", "Gijduvon"],
    "Samarqand": ["Samarqand sh.", "Kattaqo'rg'on", "Urgut"],
    "Andijon": ["Andijon sh.", "Asaka", "Shahrixon"]
}

def get_region_kb():
    buttons = [[KeyboardButton(text=r)] for r in REGIONS.keys()]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- ADMIN KOMANDASI ---
@dp.message(F.from_user.id == ADMIN_ID, Command("admin"))
async def admin_start(message: types.Message):
    await message.answer("🛠 **Boshqaruv paneli:**", reply_markup=admin_inline_kb())

# --- CALLBACKLAR (Admin Tugmalari uchun) ---
@dp.callback_query(F.from_user.id == ADMIN_ID)
async def admin_callback(call: types.CallbackQuery, state: FSMContext):
    if call.data == "admin_stat":
        conn = sqlite3.connect("bot_base.db")
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        await call.message.answer(f"📊 Jami foydalanuvchilar: {count} ta")
    
    elif call.data == "admin_send_ads":
        await state.set_state(AdminStates.waiting_for_ads)
        await call.message.answer("📝 Reklama matnini yuboring:")
    
    elif call.data == "admin_add_ch":
        await state.set_state(AdminStates.waiting_for_channel)
        await call.message.answer("🔗 Kanal username'ini yuboring (masalan: @kanaluz):")

    elif call.data == "admin_set_photo":
        await state.set_state(AdminStates.waiting_for_photo_region)
        await call.message.answer("🖼 Qaysi viloyat uchun rasm qo'ymoqchisiz? (Nomini yozing):")
    
    await call.answer()

# --- ADMIN INPUTLARINI QABUL QILISH ---
@dp.message(AdminStates.waiting_for_ads)
async def process_ads(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("bot_base.db")
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    
    count = 0
    for u in users:
        try:
            await bot.send_message(u[0], message.text)
            count += 1
        except: pass
    await message.answer(f"✅ Reklama {count} kishiga yuborildi.")
    await state.clear()

@dp.message(AdminStates.waiting_for_channel)
async def process_ch(message: types.Message, state: FSMContext):
    ch = message.text.strip()
    if ch.startswith("@"):
        conn = sqlite3.connect("bot_base.db")
        conn.execute("INSERT OR IGNORE INTO channels (username) VALUES (?)", (ch,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ {ch} majburiy obunaga qo'shildi.")
    else:
        await message.answer("❌ Xato! Username @ bilan boshlanishi kerak.")
    await state.clear()

@dp.message(AdminStates.waiting_for_photo_region)
async def process_photo_region(message: types.Message, state: FSMContext):
    if message.text in REGIONS:
        await state.update_data(region_name=message.text)
        await state.set_state(AdminStates.waiting_for_photo)
        await message.answer(f"📸 Endi {message.text} uchun rasm yuboring:")
    else:
        await message.answer("❌ Bunday viloyat yo'q. Qayta urinib ko'ring.")

@dp.message(AdminStates.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    region = data['region_name']
    photo_id = message.photo[-1].file_id
    
    conn = sqlite3.connect("bot_base.db")
    conn.execute("INSERT OR REPLACE INTO region_photos (region, photo_id) VALUES (?, ?)", (region, photo_id))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ {region} uchun rasm muvaffaqiyatli saqlandi!")
    await state.clear()

# --- FOYDALANUVCHI QISMI (START VA OB-HAVO) ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    # Foydalanuvchini bazaga qo'shish
    conn = sqlite3.connect("bot_base.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    
    # Obuna tekshirish (oldingi mantiq kabi)
    await message.answer("🇺🇿 Viloyatni tanlang:", reply_markup=get_region_kb())

@dp.message()
async def weather_handler(message: types.Message):
    city = message.text
    # Ob-havo API so'rovi bu yerda davom etadi...
    # (Yuqoridagi kod bilan bir xil, lang='uz' va emojilar bilan)
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API}&units=metric&lang=uz"
    try:
        res = requests.get(url).json()
        if res.get("main"):
            temp = res["main"]["temp"]
            hum = res["main"]["humidity"]
            desc = res["weather"][0]["description"]
            icon = "🌤" if "bulut" in desc.lower() else "☀️"
            
            msg = f"📍 {city}\n{icon} Holat: {desc.capitalize()}\n🌡 Harorat: {temp}°C\n💧 Namlik: {hum}%"
            await message.answer(msg)
    except: pass

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
