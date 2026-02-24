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
    "clear sky": "Musaffo osmon",
    "few clouds": "Biroz bulutli",
    "scattered clouds": "Tarqoq bulutli",
    "broken clouds": "Bulutli",
    "overcast clouds": "Qalin bulutli",
    "light rain": "Yengil yomg'ir",
    "moderate rain": "O'rtacha yomg'ir",
    "heavy intensity rain": "Kuchli yomg'ir",
    "thunderstorm": "Momaqaldiroq",
    "snow": "Qor",
    "mist": "Tuman"
}

# --- SQLITE VA KLAVIATURALAR (Oldingi koddagidek) ---
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect("bot_base.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return res

REGIONS = {
    "Toshkent": ["Toshkent sh.", "Chirchiq", "Angren", "Olmaliq"],
    "Buxoro": ["Buxoro sh.", "Vobkent", "Romitan", "Gijduvon"],
    "Samarqand": ["Samarqand sh.", "Kattaqo'rg'on", "Urgut"],
    "Andijon": ["Andijon sh.", "Asaka", "Shahrixon"]
}

# --- OB-HAVO FUNKSIYALARI ---
def get_weather_desc(desc_eng):
    return WEATHER_DESC.get(desc_eng.lower(), desc_eng.capitalize())

def get_emoji(desc_eng):
    desc = desc_eng.lower()
    if "clear" in desc: return "☀️"
    if "cloud" in desc: return "☁️"
    if "rain" in desc: return "🌧"
    if "snow" in desc: return "❄️"
    if "thunder" in desc: return "⚡️"
    return "🌈"

# --- ASOSIY MANTIQ ---
@dp.message(F.text.in_([d for sub in REGIONS.values() for d in sub] + list(REGIONS.keys())))
async def weather_handler(message: types.Message):
    city = message.text
    # API uchun moslash (masalan Romitan -> Romitayn)
    city_map = {"Romitan": "Romitayn", "Vobkent": "Vabkent", "Toshkent sh.": "Tashkent"}
    search_city = city_map.get(city, city)

    # 1. Hozirgi ob-havo
    current_url = f"https://api.openweathermap.org/data/2.5/weather?q={search_city}&appid={WEATHER_API}&units=metric"
    # 2. 5 kunlik prognoz (Haftalik uchun)
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={search_city}&appid={WEATHER_API}&units=metric"

    try:
        curr_res = requests.get(current_url).json()
        if curr_res.get("main"):
            # Hozirgi holat
            temp = curr_res['main']['temp']
            hum = curr_res['main']['humidity']
            desc_eng = curr_res['weather'][0]['description']
            desc_uz = get_weather_desc(desc_eng)
            emoji = get_emoji(desc_eng)

            current_text = (f"📍 **{city}**\n"
                            f"{emoji} **Holat:** {desc_uz}\n"
                            f"🌡 **Harorat:** {temp}°C\n"
                            f"💧 **Namlik:** {hum}%\n\n"
                            f"📅 **5 kunlik bashorat:**\n"
                            f"━━━━━━━━━━━━━━━\n")

            # Haftalik (5 kunlik) qism
            fore_res = requests.get(forecast_url).json()
            forecasts = fore_res.get("list", [])
            
            # Har kungi soat 12:00 dagi ma'lumotni olamiz
            added_days = []
            for item in forecasts:
                date_txt = item['dt_txt'] # 2024-03-20 12:00:00
                date_obj = datetime.strptime(date_txt, '%Y-%m-%d %H:%M:%S')
                day_name = date_obj.strftime('%d-%m') # 20-03
                
                if date_obj.hour == 12 and day_name not in added_days:
                    f_temp = item['main']['temp']
                    f_desc = get_weather_desc(item['weather'][0]['description'])
                    f_emoji = get_emoji(item['weather'][0]['description'])
                    
                    current_text += f"🗓 {day_name} | {f_emoji} {f_temp}°C | {f_desc}\n"
                    added_days.append(day_name)

            await message.answer(current_text, parse_mode="Markdown")
        else:
            await message.answer("❌ Shahar topilmadi. Iltimos lotincha yozib ko'ring.")
    except Exception as e:
        await message.answer("⚠️ Ma'lumot olishda xatolik yuz berdi.")

# (Admin panel va start qismlari avvalgi koddagidek qoladi)
