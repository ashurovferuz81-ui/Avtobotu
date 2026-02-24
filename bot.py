import sqlite3
import requests
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = '8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU'
WEATHER_API = 'a488ffc4473fa950a0c76d19b0bad387'
ADMIN_ID = 5775388579  # Sizning ID raqamingiz
CHANNELS = ["@kanal_username"]  # BU YERGA KANALINGIZ USERNAME-INI YOZING (BOSHIDA @ BILAN)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- SQLITE BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect("bot_base.db")
    curr = conn.cursor()
    curr.execute('''CREATE TABLE IF NOT EXISTS users 
                    (user_id INTEGER PRIMARY KEY, city TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect("bot_base.db")
    curr = conn.cursor()
    curr.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# --- OBUNA TEKSHIRISH FUNKSIYASI ---
async def check_sub(user_id):
    if not CHANNELS: return True
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            # Agar bot kanalga admin bo'lmasa yoki xato bo'lsa
            return True 
    return True

# --- /START KOMANDASI ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    
    if not await check_sub(message.from_user.id):
        buttons = []
        for ch in CHANNELS:
            buttons.append([InlineKeyboardButton(text="Kanalga obuna bo'lish", url=f"https://t.me/{ch[1:]}")])
        buttons.append([InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_sub")])
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(f"Assalomu alaykum, {message.from_user.full_name}!\nBotdan foydalanish uchun kanalimizga obuna bo'ling:", reply_markup=kb)
        return

    await message.answer("Xush kelibsiz! Ob-havoni bilish uchun shahar nomini yozing (masalan: Tashkent).")

# --- OBUNANI TEKSHIRISH (CALLBACK) ---
@dp.callback_query(F.data == "check_sub")
async def check_callback(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await call.message.answer("Rahmat! Endi shahar nomini yozib yuboring.")
    else:
        await call.answer("Siz hali obuna bo'lmadingiz!", show_alert=True)

# --- ADMIN PANEL VA REKLAMA ---
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect("bot_base.db")
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        await message.answer(f"📊 **Statistika:**\n\nFoydalanuvchilar: {count} ta\n\nReklama yuborish uchun: `/send [matn]`")

@dp.message(Command("send"))
async def send_ads(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        text = message.text.replace("/send", "").strip()
        if not text:
            await message.answer("Reklama matnini yozing. Masalan: `/send Salom hammaga`")
            return
            
        conn = sqlite3.connect("bot_base.db")
        users = conn.execute("SELECT user_id FROM users").fetchall()
        conn.close()
        
        count = 0
        for user in users:
            try:
                await bot.send_message(user[0], text)
                count += 1
                await asyncio.sleep(0.05) # Spamga tushmaslik uchun
            except Exception:
                pass
        await message.answer(f"✅ Reklama {count} ta foydalanuvchiga yuborildi.")

# --- OB-HAVO QIDIRUVI ---
@dp.message()
async def weather_logic(message: types.Message):
    # Obunani tekshirish
    if not await check_sub(message.from_user.id):
        await start_cmd(message)
        return

    city = message.text
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API}&units=metric&lang=uz"
    
    try:
        res = requests.get(url).json()
        if res.get("main"):
            temp = res["main"]["temp"]
            feels_like = res["main"]["feels_like"]
            desc = res["weather"][0]["description"]
            humidity = res["main"]["humidity"]
            
            text = (f"🌤 **Shahar:** {city.capitalize()}\n"
                    f"🌡 **Harorat:** {temp}°C\n"
                    f"🤔 **Sezilishi:** {feels_like}°C\n"
                    f"📝 **Holat:** {desc.capitalize()}\n"
                    f"💧 **Namlik:** {humidity}%")
            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer("❌ Shahar topilmadi. Iltimos, shahar nomini to'g'ri yozing (masalan: Samarkand).")
    except Exception:
        await message.answer("⚠️ Ma'lumot olishda xatolik yuz berdi.")

# --- ISHGA TUSHIRISH ---
async def main():
    init_db()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
