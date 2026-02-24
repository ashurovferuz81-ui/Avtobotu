import sqlite3
import requests
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# --- SOZLAMALAR ---
API_TOKEN = '8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU'
WEATHER_API = 'a488ffc4473fa950a0c76d19b0bad387'
ADMIN_ID = 5775388579
CHANNELS = ["@kanal_username"] # O'z kanalingizni yozing

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR STRUKTURASI (Viloyat va tumanlar) ---
REGIONS = {
    "Toshkent": {
        "img": "https://storage.googleapis.com/railway-uz/tashkent.jpg", # Rasm manzili
        "districts": ["Toshkent sh.", "Chirchiq", "Angren", "Olmaliq", "Bekobod", "Yangiyo'l"]
    },
    "Buxoro": {
        "img": "https://storage.googleapis.com/railway-uz/bukhara.jpg",
        "districts": ["Buxoro sh.", "Vobkent", "Romitan", "Gijduvon", "Olot", "Qorako'l"]
    },
    "Samarqand": {
        "img": "https://storage.googleapis.com/railway-uz/samarkand.jpg",
        "districts": ["Samarqand sh.", "Kattaqo'rg'on", "Urgut", "Pastdarg'om", "Bulung'ur"]
    }
    # Boshqa viloyatlarni ham shu tarzda qo'shish mumkin
}

# --- SQLITE BAZA ---
def init_db():
    conn = sqlite3.connect("bot_base.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()

# --- TUGMALAR ---
def region_kb():
    buttons = []
    r_list = list(REGIONS.keys())
    for i in range(0, len(r_list), 2):
        row = [KeyboardButton(text=r_list[i])]
        if i+1 < len(r_list): row.append(KeyboardButton(text=r_list[i+1]))
        buttons.append(row)
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def district_kb(region):
    buttons = []
    districts = REGIONS[region]["districts"]
    for i in range(0, len(districts), 2):
        row = [KeyboardButton(text=districts[i])]
        if i+1 < len(districts): row.append(KeyboardButton(text=districts[i+1]))
        buttons.append(row)
    buttons.append([KeyboardButton(text="⬅️ Orqaga")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- MAJBURIY OBUNA ---
async def check_sub(user_id):
    for ch in CHANNELS:
        try:
            m = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if m.status in ['left', 'kicked']: return False
        except: continue
    return True

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    conn = sqlite3.connect("bot_base.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()

    if not await check_sub(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{CHANNELS[0][1:]}")],
            [InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")]
        ])
        await message.answer("Botdan foydalanish uchun kanalimizga a'zo bo'ling!", reply_markup=kb)
        return
    await message.answer("🇺🇿 Viloyatingizni tanlang:", reply_markup=region_kb())

# --- VILOYAT TANLANGANDA ---
@dp.message(F.text.in_(REGIONS.keys()))
async def select_region(message: types.Message):
    region = message.text
    await message.answer_photo(
        photo=REGIONS[region]["img"],
        caption=f"📍 {region} viloyati tanlandi.\nEndi tumanni tanlang:",
        reply_markup=district_kb(region)
    )

@dp.message(F.text == "⬅️ Orqaga")
async def back_to_regions(message: types.Message):
    await message.answer("🇺🇿 Viloyatni tanlang:", reply_markup=region_kb())

# --- OB-HAVO MANTIQI (Tumanlar va yozilgan shaharlar uchun) ---
@dp.message()
async def weather_handler(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        if message.text.startswith("/send"):
            text = message.text.replace("/send", "").strip()
            conn = sqlite3.connect("bot_base.db")
            users = conn.execute("SELECT user_id FROM users").fetchall()
            for u in users:
                try: await bot.send_message(u[0], text)
                except: pass
            return await message.answer("✅ Reklama yuborildi!")
        elif message.text == "/admin":
            conn = sqlite3.connect("bot_base.db")
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            return await message.answer(f"📊 Foydalanuvchilar: {count} ta")

    city = message.text
    # API uchun lotincha nomga o'girish (sodda xarita)
    map_names = {"Toshkent sh.": "Tashkent", "Buxoro sh.": "Bukhara", "Samarqand sh.": "Samarkand", "Vobkent": "Vabkent"}
    search_name = map_names.get(city, city)

    url = f"https://api.openweathermap.org/data/2.5/weather?q={search_name}&appid={WEATHER_API}&units=metric&lang=uz"
    
    try:
        res = requests.get(url).json()
        if res.get("main"):
            temp = res["main"]["temp"]
            hum = res["main"]["humidity"]
            desc = res["weather"][0]["description"]
            wind = res["wind"]["speed"]
            rain = res.get("rain", {}).get("1h", 0) # Oxirgi 1 soatdagi yomg'ir miqdori

            # Emojilarni holatga qarab tanlash
            icon = "☀️"
            if "bulut" in desc.lower(): icon = "☁️"
            if "yomg'ir" in desc.lower(): icon = "🌧"
            if "qor" in desc.lower(): icon = "❄️"

            text = (f"🌈 **{city.upper()}**\n\n"
                    f"{icon} **Holat:** {desc.capitalize()}\n"
                    f"🌡 **Harorat:** {temp}°C\n"
                    f"💧 **Namlik:** {hum}%\n"
                    f"💨 **Shamol:** {wind} m/s\n")
            
            if rain > 0:
                text += f"☔️ **Yomg'ir:** {rain} mm/soat"

            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("🤷‍♂️ Shahar nomi xato yoki ma'lumot topilmadi.")
    except:
        await message.answer("⚠️ Xizmatda uzilish yuz berdi.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
