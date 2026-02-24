import sqlite3
import requests
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = '8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU'
WEATHER_API = 'a488ffc4473fa950a0c76d19b0bad387'
ADMIN_ID = 5775388579
CHANNELS = ["@kanal_username"] # O'z kanalingizni yozing yoki bo'sh qoldiring []

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Doimiy chiqib turadigan asosiy shaharlar
DEFAULT_CITIES = ["Toshkent", "Samarqand", "Buxoro", "Andijon", "Namangan", "Farg'ona", "Xiva", "Nukus"]

# --- SQLITE BAZA ---
def init_db():
    conn = sqlite3.connect("bot_base.db")
    curr = conn.cursor()
    curr.execute('''CREATE TABLE IF NOT EXISTS users 
                    (user_id INTEGER PRIMARY KEY, last_city TEXT)''')
    curr.execute('''CREATE TABLE IF NOT EXISTS history 
                    (user_id INTEGER, city TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect("bot_base.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def save_to_history(user_id, city):
    conn = sqlite3.connect("bot_base.db")
    check = conn.execute("SELECT * FROM history WHERE user_id=? AND city=?", (user_id, city)).fetchone()
    if not check:
        conn.execute("INSERT INTO history (user_id, city) VALUES (?, ?)", (user_id, city))
    conn.commit()
    conn.close()

# --- MENU TUGMALARI ---
def get_weather_keyboard(user_id):
    # Asosiy shaharlarni qo'shamiz
    buttons = []
    row = []
    
    # 1. Standart shaharlar
    for city in DEFAULT_CITIES:
        row.append(KeyboardButton(text=city))
        if len(row) == 2:
            buttons.append(row)
            row = []
            
    # 2. Foydalanuvchi o'zi yozgan oxirgi 2 ta shaharni ham qo'shish (ixtiyoriy)
    conn = sqlite3.connect("bot_base.db")
    user_cities = conn.execute("SELECT city FROM history WHERE user_id=? AND city NOT IN ({}) ORDER BY rowid DESC LIMIT 2".format(','.join(['?']*len(DEFAULT_CITIES))), (user_id, *DEFAULT_CITIES)).fetchall()
    conn.close()
    
    for c in user_cities:
        buttons.append([KeyboardButton(text=c[0])])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- MAJBURIY OBUNA ---
async def check_sub(user_id):
    if not CHANNELS: return True
    for ch in CHANNELS:
        try:
            m = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if m.status in ['left', 'kicked']: return False
        except: return True
    return True

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    if not await check_sub(message.from_user.id):
        btn = [[InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{CHANNELS[0][1:]}")],
               [InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")]]
        await message.answer("Botdan foydalanish uchun kanalga a'zo bo'ling!", reply_markup=InlineKeyboardMarkup(inline_keyboard=btn))
        return
    
    await message.answer("Salom! Quyidagi shaharlardan birini tanlang yoki shahar nomini yozing:", 
                         reply_markup=get_weather_keyboard(message.from_user.id))

# --- OBUNANI TEKSHIRISH (CALLBACK) ---
@dp.callback_query(F.data == "check_sub")
async def check_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await call.message.answer("Rahmat! Shaharni tanlang:", reply_markup=get_weather_keyboard(call.from_user.id))
    else:
        await call.answer("Siz hali obuna bo'lmadingiz!", show_alert=True)

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect("bot_base.db")
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        await message.answer(f"📊 Statistika\nFoydalanuvchilar: {count}\nReklama: `/send xabar`")

@dp.message(Command("send"))
async def send_ads(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        text = message.text.replace("/send", "").strip()
        conn = sqlite3.connect("bot_base.db")
        users = conn.execute("SELECT user_id FROM users").fetchall()
        conn.close()
        for u in users:
            try: await bot.send_message(u[0], text)
            except: pass
        await message.answer("Yuborildi!")

# --- OB-HAVO MANTIQI ---
@dp.message()
async def handle_weather(message: types.Message):
    if not await check_sub(message.from_user.id):
        return await start_cmd(message)

    city = message.text
    # Shahar nomini inglizchaga o'girish (oddiy variant)
    city_map = {"Toshkent": "Tashkent", "Samarqand": "Samarkand", "Buxoro": "Bukhara", "Farg'ona": "Fergana", "Andijon": "Andijan"}
    search_city = city_map.get(city, city)

    url = f"https://api.openweathermap.org/data/2.5/weather?q={search_city}&appid={WEATHER_API}&units=metric&lang=uz"
    
    try:
        res = requests.get(url).json()
        if res.get("main"):
            save_to_history(message.from_user.id, city) # Bazaga saqlash
            
            temp = res["main"]["temp"]
            desc = res["weather"][0]["description"]
            hum = res["main"]["humidity"]
            
            msg = f"📍 {city}\n🌡 Harorat: {temp}°C\n💧 Namlik: {hum}%\n☁️ Holat: {desc.capitalize()}"
            await message.answer(msg, reply_markup=get_weather_keyboard(message.from_user.id))
        else:
            await message.answer("❌ Shahar topilmadi. Shahar nomini lotincha yozing (Masalan: Tashkent).")
    except:
        await message.answer("Xatolik yuz berdi.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
