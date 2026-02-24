import sqlite3
import requests
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, 
                           ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)

# --- SOZLAMALAR ---
API_TOKEN = '8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU'
WEATHER_API = 'a488ffc4473fa950a0c76d19b0bad387'
ADMIN_ID = 5775388579

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- FSM (Holatlar) ---
class AdminStates(StatesGroup):
    waiting_for_ads = State()
    waiting_for_channel = State()
    waiting_for_photo_region = State()
    waiting_for_photo = State()

# --- SQLITE BAZA FUNKSIYALARI ---
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return res

def init_db():
    db_query("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    db_query("CREATE TABLE IF NOT EXISTS channels (username TEXT PRIMARY KEY)")
    db_query("CREATE TABLE IF NOT EXISTS region_photos (region TEXT PRIMARY KEY, photo_id TEXT)")

# --- KLAVIATURALAR ---
REGIONS = {
    "Toshkent": ["Toshkent sh.", "Chirchiq", "Angren", "Olmaliq"],
    "Buxoro": ["Buxoro sh.", "Vobkent", "Romitan", "Gijduvon"],
    "Samarqand": ["Samarqand sh.", "Kattaqo'rg'on", "Urgut"],
    "Andijon": ["Andijon sh.", "Asaka", "Shahrixon"]
}

def get_main_kb(user_id):
    buttons = []
    r_list = list(REGIONS.keys())
    for i in range(0, len(r_list), 2):
        row = [KeyboardButton(text=r_list[i])]
        if i+1 < len(r_list): row.append(KeyboardButton(text=r_list[i+1]))
        buttons.append(row)
    
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def admin_inline_kb():
    kb = [
        [InlineKeyboardButton(text="📢 Reklama", callback_data="ads"),
         InlineKeyboardButton(text="➕ Kanal", callback_data="add_ch")],
        [InlineKeyboardButton(text="🖼 Rasm qo'yish", callback_data="set_p"),
         InlineKeyboardButton(text="📊 Statistika", callback_data="stat")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- MAJBURIY OBUNA TEKSHIRISH ---
async def is_subscribed(user_id):
    channels = db_query("SELECT username FROM channels", fetch=True)
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch[0], user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except: continue
    return True

# --- START ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    db_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    if not await is_subscribed(message.from_user.id):
        channels = db_query("SELECT username FROM channels", fetch=True)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{c[0][1:]}")] for c in channels
        ])
        kb.inline_keyboard.append([InlineKeyboardButton(text="Tekshirish ✅", callback_data="check")])
        return await message.answer("Botdan foydalanish uchun obuna bo'ling:", reply_markup=kb)
    
    await message.answer("Xush kelibsiz! Viloyatni tanlang:", reply_markup=get_main_kb(message.from_user.id))

# --- ADMIN PANEL (REPLY TUGMA ORQALI) ---
@dp.message(F.text == "⚙️ Admin Panel", F.from_user.id == ADMIN_ID)
async def admin_menu(message: types.Message):
    await message.answer("🛠 Admin boshqaruv paneli:", reply_markup=admin_inline_kb())

# --- CALLBACKS ---
@dp.callback_query(F.data == "check")
async def check_callback(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        await call.message.delete()
        await call.message.answer("Rahmat! Endi botdan foydalanishingiz mumkin.", reply_markup=get_main_kb(call.from_user.id))
    else:
        await call.answer("Hali obuna bo'lmadingiz!", show_alert=True)

@dp.callback_query(F.from_user.id == ADMIN_ID)
async def admin_callbacks(call: types.CallbackQuery, state: FSMContext):
    if call.data == "ads":
        await call.message.answer("Reklama matnini yuboring:")
        await state.set_state(AdminStates.waiting_for_ads)
    elif call.data == "add_ch":
        await call.message.answer("Kanal username'ini yuboring (@kanaluz):")
        await state.set_state(AdminStates.waiting_for_channel)
    elif call.data == "set_p":
        await call.message.answer("Qaysi viloyat? (Masalan: Toshkent):")
        await state.set_state(AdminStates.waiting_for_photo_region)
    elif call.data == "stat":
        count = db_query("SELECT COUNT(*) FROM users", fetch=True)[0][0]
        await call.message.answer(f"📊 Foydalanuvchilar: {count} ta")
    await call.answer()

# --- ADMIN PROCESSORS (FSM) ---
@dp.message(AdminStates.waiting_for_ads)
async def ads_process(message: types.Message, state: FSMContext):
    users = db_query("SELECT user_id FROM users", fetch=True)
    for u in users:
        try: await bot.send_message(u[0], message.text)
        except: pass
    await message.answer("✅ Yuborildi!")
    await state.clear()

@dp.message(AdminStates.waiting_for_channel)
async def ch_process(message: types.Message, state: FSMContext):
    if message.text.startswith("@"):
        db_query("INSERT OR IGNORE INTO channels (username) VALUES (?)", (message.text,))
        await message.answer("✅ Kanal qo'shildi!")
    else: await message.answer("❌ Xato! @ bilan yozing.")
    await state.clear()

@dp.message(AdminStates.waiting_for_photo_region)
async def photo_reg_process(message: types.Message, state: FSMContext):
    if message.text in REGIONS:
        await state.update_data(reg=message.text)
        await message.answer(f"🖼 {message.text} uchun rasm yuboring:")
        await state.set_state(AdminStates.waiting_for_photo)
    else: await message.answer("❌ Bunday viloyat yo'q.")

@dp.message(AdminStates.waiting_for_photo, F.photo)
async def photo_save_process(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db_query("INSERT OR REPLACE INTO region_photos (region, photo_id) VALUES (?, ?)", (data['reg'], message.photo[-1].file_id))
    await message.answer(f"✅ {data['reg']} uchun rasm saqlandi!")
    await state.clear()

# --- WEATHER LOGIC ---
@dp.message(F.text.in_(REGIONS.keys()))
async def show_weather_region(message: types.Message):
    region = message.text
    photo = db_query("SELECT photo_id FROM region_photos WHERE region=?", (region,), fetch=True)
    
    # Tumanlar tugmalari
    t_buttons = [[KeyboardButton(text=d)] for d in REGIONS[region]]
    t_buttons.append([KeyboardButton(text="⬅️ Orqaga")])
    kb = ReplyKeyboardMarkup(keyboard=t_buttons, resize_keyboard=True)

    if photo:
        await message.answer_photo(photo[0][0], caption=f"📍 {region} tumanini tanlang:", reply_markup=kb)
    else:
        await message.answer(f"📍 {region} tumanini tanlang:", reply_markup=kb)

@dp.message(F.text == "⬅️ Orqaga")
async def back_cmd(message: types.Message):
    await message.answer("Viloyatni tanlang:", reply_markup=get_main_kb(message.from_user.id))

@dp.message()
async def weather_final(message: types.Message):
    if not await is_subscribed(message.from_user.id): return
    city = message.text
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API}&units=metric&lang=uz"
    try:
        res = requests.get(url).json()
        if res.get("main"):
            t = res['main']['temp']
            h = res['main']['humidity']
            d = res['weather'][0]['description']
            icon = "☀️" if "ochiq" in d.lower() else "☁️"
            if "yomg" in d.lower(): icon = "🌧"
            await message.answer(f"📍 {city}\n{icon} Holat: {d.capitalize()}\n🌡 Harorat: {t}°C\n💧 Namlik: {h}%")
    except: pass

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
