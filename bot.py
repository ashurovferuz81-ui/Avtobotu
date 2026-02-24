import sqlite3
import requests
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, 
                           ReplyKeyboardMarkup, KeyboardButton)

# --- SOZLAMALAR ---
API_TOKEN = '8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU'
WEATHER_API = 'a488ffc4473fa950a0c76d19b0bad387'
ADMIN_ID = 5775388579

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- TARJIMON LUG'ATI ---
WEATHER_DESC = {
    "clear sky": "Musaffo osmon", "few clouds": "Biroz bulutli", "scattered clouds": "Tarqoq bulutli",
    "broken clouds": "Bulutli", "overcast clouds": "Qalin bulutli", "light rain": "Yengil yomg'ir",
    "moderate rain": "O'rtacha yomg'ir", "heavy intensity rain": "Kuchli yomg'ir", "thunderstorm": "Momaqaldiroq",
    "snow": "Qor", "mist": "Tuman", "fog": "Qalin tuman"
}

# --- VILOYAT VA TUMANLAR ---
REGIONS = {
    "Toshkent": ["Toshkent sh.", "Angren", "Olmaliq", "Bekobod", "Chirchiq", "Yangiyo'l"],
    "Buxoro": ["Buxoro sh.", "Kogon", "Olot", "Gijduvon", "Jondor", "Qorako'l", "Romiton", "Vobkent"],
    "Samarqand": ["Samarqand sh.", "Kattaqo'rg'on", "Urgut", "Ishtixon", "Jomboy", "Bulung'ur"],
    "Andijon": ["Andijon sh.", "Asaka", "Shahrixon", "Xonobod", "Paxtaobod"],
    "Farg'ona": ["Farg'ona sh.", "Marg'ilon", "Qo'qon", "Quva", "Rishton", "Oltiariq"],
    "Namangan": ["Namangan sh.", "Chortoq", "Chust", "Kosonsoy", "Pop", "Uychi"],
    "Qashqadaryo": ["Karshi", "Dehqonobod", "Kitob", "Koson", "Muborak", "Shahrisabz"],
    "Surxondaryo": ["Termiz", "Denov", "Boysun", "Jarqo'rg'on", "Sherobod", "Sho'rchi"],
    "Xorazm": ["Urganch", "Xiva", "Bog'ot", "Gurlan", "Shovot", "Xonqa"],
    "Navoiy": ["Navoiy sh.", "Zarafshon", "Karmana", "Qiziltepa", "Nurota", "Uchkuduk"],
    "Jizzax": ["Jizzax sh.", "Baxmal", "G'allaorol", "Zomin", "Forish", "Do'stlik"],
    "Sirdaryo": ["Guliston", "Shirin", "Yangiyer", "Boyovut", "Sayhunobod", "Xovos"],
    "Qoraqalpog'iston": ["Nukus", "Beruniy", "Mo'ynoq", "Qo'ng'irot", "To'rtko'l", "Xo'jayli"]
}

# --- SQLITE VA ADMIN FUNKSIYALARI ---
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

class AdminStates(StatesGroup):
    waiting_for_ads = State(); waiting_for_channel = State()
    waiting_for_photo_region = State(); waiting_for_photo = State()

def get_main_kb(user_id):
    buttons = []
    r_list = list(REGIONS.keys())
    for i in range(0, len(r_list), 2):
        row = [KeyboardButton(text=r_list[i])]
        if i+1 < len(r_list): row.append(KeyboardButton(text=r_list[i+1]))
        buttons.append(row)
    if user_id == ADMIN_ID: buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_districts_kb(region):
    buttons = []
    districts = REGIONS[region]
    for i in range(0, len(districts), 2):
        row = [KeyboardButton(text=districts[i])]
        if i+1 < len(districts): row.append(KeyboardButton(text=districts[i+1]))
        buttons.append(row)
    buttons.append([KeyboardButton(text="⬅️ Orqaga")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def is_subscribed(user_id):
    channels = db_query("SELECT username FROM channels", fetch=True)
    if not channels: return True
    for ch in channels:
        try:
            m = await bot.get_chat_member(chat_id=ch[0], user_id=user_id)
            if m.status in ['left', 'kicked']: return False
        except: continue
    return True

# --- START ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    db_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    if not await is_subscribed(message.from_user.id):
        channels = db_query("SELECT username FROM channels", fetch=True)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"Obuna: {c[0]}", url=f"https://t.me/{c[0][1:]}")] for c in channels])
        kb.inline_keyboard.append([InlineKeyboardButton(text="Tekshirish ✅", callback_data="check")])
        return await message.answer("Botdan foydalanish uchun obuna bo'ling:", reply_markup=kb)
    await message.answer("🇺🇿 Shaxar tanlang yoki nomini yozing:", reply_markup=get_main_kb(message.from_user.id))

@dp.callback_query(F.data == "check")
async def check_sub_cb(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        await call.message.delete()
        await call.message.answer("Xush kelibsiz!", reply_markup=get_main_kb(call.from_user.id))
    else: await call.answer("Obuna bo'lmagansiz!", show_alert=True)

# --- VILOYAT TANLASH ---
@dp.message(F.text.in_(REGIONS.keys()))
async def select_region(message: types.Message):
    region = message.text
    photo = db_query("SELECT photo_id FROM region_photos WHERE region=?", (region,), fetch=True)
    if photo: await message.answer_photo(photo[0][0], caption=f"📍 {region} tumanlari:", reply_markup=get_districts_kb(region))
    else: await message.answer(f"📍 {region} tumanlari:", reply_markup=get_districts_kb(region))

@dp.message(F.text == "⬅️ Orqaga")
async def go_back(message: types.Message):
    await message.answer("Viloyatni tanlang:", reply_markup=get_main_kb(message.from_user.id))

# --- OB-HAVO MANTIQI (ASOSIY) ---
@dp.message()
async def show_weather(message: types.Message, state: FSMContext):
    # Admin Panel kirishi
    if message.text == "⚙️ Admin Panel" and message.from_user.id == ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Reklama", callback_data="ads"), InlineKeyboardButton(text="➕ Kanal", callback_data="add_ch")],
            [InlineKeyboardButton(text="🖼 Rasm qo'yish", callback_data="set_p"), InlineKeyboardButton(text="📊 Stat", callback_data="stat")]
        ])
        return await message.answer("🛠 Admin Paneli:", reply_markup=kb)

    if not await is_subscribed(message.from_user.id): return

    city = message.text
    # API uchun Romiton va boshqalarni to'g'irlash
    city_map = {"Romitan": "Romitayn", "Vobkent": "Vabkent", "Toshkent sh.": "Tashkent", "Karshi": "Qarshi"}
    search = city_map.get(city, city)

    url = f"https://api.openweathermap.org/data/2.5/weather?q={search}&appid={WEATHER_API}&units=metric"
    fore = f"https://api.openweathermap.org/data/2.5/forecast?q={search}&appid={WEATHER_API}&units=metric"

    try:
        r = requests.get(url).json()
        if r.get("main"):
            temp = r['main']['temp']
            hum = r['main']['humidity']
            desc_en = r['weather'][0]['description'].lower()
            desc_uz = WEATHER_DESC.get(desc_en, desc_en.capitalize())
            
            icon = "☀️" if "clear" in desc_en else "☁️"
            if "rain" in desc_en: icon = "🌧"
            if "snow" in desc_en: icon = "❄️"

            res_text = (f"📍 **{city}**\n{icon} **Holat:** {desc_uz}\n🌡 **Harorat:** {temp}°C\n💧 **Namlik:** {hum}%\n\n📅 **Kelgusi kunlar:**\n━━━━━━━━━━━━━━━\n")
            
            f_res = requests.get(fore).json()
            added = []
            for item in f_res.get("list", []):
                dt = datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S')
                day = dt.strftime('%d-%m')
                if dt.hour == 12 and day not in added:
                    f_temp = item['main']['temp']
                    f_en = item['weather'][0]['description'].lower()
                    f_uz = WEATHER_DESC.get(f_en, "Ochiq havo")
                    res_text += f"🗓 {day} | {f_temp}°C | {f_uz}\n"
                    added.append(day)
            await message.answer(res_text, parse_mode="Markdown")
        else:
            await message.answer("❌ Shahar topilmadi. Iltimos, nomini to'g'ri yozing (Masalan: USA, Moscow, London).")
    except:
        await message.answer("⚠️ Ma'lumot olishda xatolik. Keyinroq urinib ko'ring.")

# --- ADMIN PANEL CALLBACKS VA STATES ---
@dp.callback_query(F.from_user.id == ADMIN_ID)
async def admin_calls(call: types.CallbackQuery, state: FSMContext):
    if call.data == "ads": await state.set_state(AdminStates.waiting_for_ads); await call.message.answer("Reklama matnini yuboring:")
    elif call.data == "add_ch": await state.set_state(AdminStates.waiting_for_channel); await call.message.answer("Kanal username (@kanal):")
    elif call.data == "set_p": await state.set_state(AdminStates.waiting_for_photo_region); await call.message.answer("Viloyat nomi (Masalan: Buxoro):")
    elif call.data == "stat":
        c = db_query("SELECT COUNT(*) FROM users", fetch=True)[0][0]
        await call.message.answer(f"📊 Foydalanuvchilar: {c} ta")
    await call.answer()

@dp.message(AdminStates.waiting_for_ads)
async def ad_send(m: types.Message, state: FSMContext):
    users = db_query("SELECT user_id FROM users", fetch=True)
    for u in users:
        try: await bot.send_message(u[0], m.text)
        except: pass
    await m.answer("✅ Yuborildi!"); await state.clear()

@dp.message(AdminStates.waiting_for_channel)
async def ch_add(m: types.Message, state: FSMContext):
    if m.text.startswith("@"):
        db_query("INSERT OR IGNORE INTO channels (username) VALUES (?)", (m.text,))
        await m.answer("✅ Kanal qo'shildi!"); await state.clear()
    else: await m.answer("❌ @ bilan boshlanishi shart.")

@dp.message(AdminStates.waiting_for_photo_region)
async def ph_reg(m: types.Message, state: FSMContext):
    if m.text in REGIONS:
        await state.update_data(reg=m.text)
        await state.set_state(AdminStates.waiting_for_photo)
        await m.answer(f"🖼 {m.text} uchun rasm yuboring:")
    else: await m.answer("❌ Viloyat nomi xato.")

@dp.message(AdminStates.waiting_for_photo, F.photo)
async def ph_save(m: types.Message, state: FSMContext):
    d = await state.get_data()
    db_query("INSERT OR REPLACE INTO region_photos (region, photo_id) VALUES (?, ?)", (d['reg'], m.photo[-1].file_id))
    await m.answer("✅ Rasm saqlandi!"); await state.clear()

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
