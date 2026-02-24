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

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- SQLITE BAZA (Yaxshilangan) ---
def init_db():
    conn = sqlite3.connect("bot_base.db")
    # Foydalanuvchilar
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    # Majburiy obuna kanallari
    conn.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT PRIMARY KEY)")
    # Viloyat rasmlari
    conn.execute("CREATE TABLE IF NOT EXISTS region_photos (region TEXT PRIMARY KEY, photo_id TEXT)")
    conn.commit()
    conn.close()

# --- VILOYAT VA TUMANLAR ---
REGIONS = {
    "Toshkent": ["Toshkent sh.", "Chirchiq", "Angren", "Olmaliq", "Bekobod", "Yangiyo'l"],
    "Buxoro": ["Buxoro sh.", "Vobkent", "Romitan", "Gijduvon", "Olot", "Qorako'l"],
    "Samarqand": ["Samarqand sh.", "Kattaqo'rg'on", "Urgut", "Pastdarg'om", "Bulung'ur"],
    "Andijon": ["Andijon sh.", "Asaka", "Shahrixon", "Xonobod"]
}

# --- YORDAMCHI FUNKSIYALAR ---
async def check_sub(user_id):
    conn = sqlite3.connect("bot_base.db")
    channels = conn.execute("SELECT username FROM channels").fetchall()
    conn.close()
    
    for ch in channels:
        try:
            m = await bot.get_chat_member(chat_id=ch[0], user_id=user_id)
            if m.status in ['left', 'kicked']: return False
        except: continue
    return True

def get_region_kb():
    buttons = [[KeyboardButton(text=r)] for r in REGIONS.keys()]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_district_kb(region):
    buttons = [[KeyboardButton(text=d)] for d in REGIONS[region]]
    buttons.append([KeyboardButton(text="⬅️ Orqaga")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- START VA OBUNA ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    conn = sqlite3.connect("bot_base.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()

    if not await check_sub(message.from_user.id):
        conn = sqlite3.connect("bot_base.db")
        channels = conn.execute("SELECT username FROM channels").fetchall()
        conn.close()
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Kanalga o'tish", url=f"https://t.me/{ch[0][1:]}")] for ch in channels
        ])
        kb.inline_keyboard.append([InlineKeyboardButton(text="Tekshirish ✅", callback_data="check")])
        await message.answer("Botdan foydalanish uchun kanallarga a'zo bo'ling!", reply_markup=kb)
        return
    await message.answer("🇺🇿 Viloyatni tanlang:", reply_markup=get_region_kb())

# --- ADMIN PANEL ---
@dp.message(F.from_user.id == ADMIN_ID, Command("admin"))
async def admin_panel(message: types.Message):
    text = (
        "👨‍💻 **Admin Panel**\n\n"
        "📢 `/add_chan @username` - Kanal qo'shish\n"
        "❌ `/del_chan @username` - Kanalni o'chirish\n"
        "🖼 `/set_photo Viloyat_Nomi` - Rasm o'rnatish (Rasm bilan yuboring)\n"
        "📩 `/send Matn` - Reklama yuborish\n"
        "📊 `/stat` - Foydalanuvchilar soni"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.from_user.id == ADMIN_ID, Command("add_chan"))
async def add_chan(message: types.Message):
    ch = message.text.split()[-1]
    conn = sqlite3.connect("bot_base.db")
    conn.execute("INSERT OR IGNORE INTO channels (username) VALUES (?)", (ch,))
    conn.commit()
    conn.close()
    await message.answer(f"✅ {ch} kanallar ro'yxatiga qo'shildi.")

@dp.message(F.from_user.id == ADMIN_ID, F.photo, Command("set_photo"))
async def set_photo(message: types.Message):
    region = message.caption.replace("/set_photo", "").strip()
    if region in REGIONS:
        photo_id = message.photo[-1].file_id
        conn = sqlite3.connect("bot_base.db")
        conn.execute("INSERT OR REPLACE INTO region_photos (region, photo_id) VALUES (?, ?)", (region, photo_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ {region} uchun rasm saqlandi.")

# --- OB-HAVO MANTIQI ---
@dp.message(F.text.in_(REGIONS.keys()))
async def show_districts(message: types.Message):
    region = message.text
    conn = sqlite3.connect("bot_base.db")
    photo = conn.execute("SELECT photo_id FROM region_photos WHERE region=?", (region,)).fetchone()
    conn.close()
    
    if photo:
        await message.answer_photo(photo[0], caption=f"📍 {region} viloyati tumanlari:", reply_markup=get_district_kb(region))
    else:
        await message.answer(f"📍 {region} viloyati tumanlari:", reply_markup=get_district_kb(region))

@dp.message(F.text == "⬅️ Orqaga")
async def back(message: types.Message):
    await message.answer("🇺🇿 Viloyatni tanlang:", reply_markup=get_region_kb())

@dp.message()
async def weather(message: types.Message):
    if not await check_sub(message.from_user.id): return
    
    city = message.text
    # API so'rovi (lang=uz o'zbekcha tavsif beradi)
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API}&units=metric&lang=uz"
    
    try:
        res = requests.get(url).json()
        if res.get("main"):
            temp = res["main"]["temp"]
            hum = res["main"]["humidity"]
            desc = res["weather"][0]["description"]
            # "Rain" foizi API ning bepul versiyasida ba'zan 'pop' (probability of precipitation) orqali chiqadi
            # lekin standard /weather API da bu faqat 1h yoki 3h lik miqdorda bo'ladi.
            # Shuning uchun "Yog'ingarchilik ehtimoli"ni namlik va holatga qarab chiqaramiz
            
            rain_val = res.get("rain", {}).get("1h", 0)
            
            icon = "☀️"
            if "bulut" in desc.lower(): icon = "☁️"
            elif "yomg" in desc.lower(): icon = "🌧"
            elif "qor" in desc.lower(): icon = "❄️"

            text = (
                f"🌈 **Shahar:** {city}\n"
                f"{icon} **Holat:** {desc.capitalize()}\n\n"
                f"🌡 **Harorat:** {temp}°C\n"
                f"💧 **Namlik:** {hum}%\n"
                f"☔️ **Yomg'ir:** {'Yog\'moqda' if rain_val > 0 else 'Kutilmayapti'}\n"
                f"💨 **Shamol:** {res['wind']['speed']} m/s"
            )
            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("❌ Ma'lumot topilmadi.")
    except:
        await message.answer("⚠️ Xatolik.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
