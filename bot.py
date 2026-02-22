import os
import sqlite3
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- SOZLAMALAR ---
# Siz bergan yangi domen
WEBHOOK_DOMAIN = "botmeniki-sarikprok.up.railway.app" 
MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579

# --- DATABASE ---
def get_db():
    # Railway'da ma'lumotlar o'chib ketmasligi uchun database.db fayli yaratiladi
    conn = sqlite3.connect("database.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, is_premium INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS bots (bot_token TEXT PRIMARY KEY, owner_id INTEGER, type TEXT)")
    conn.commit()
    conn.close()

init_db()

# --- BOT VA DISPATCHER ---
main_bot = Bot(token=MAIN_TOKEN)
dp = Dispatcher()

# --- LIFESPAN (Railway'da barqaror ishlash uchun) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Asosiy bot uchun webhook o'rnatish
    webhook_url = f"https://{WEBHOOK_DOMAIN}/main-webhook"
    await main_bot.set_webhook(url=webhook_url, drop_pending_updates=True)
    logging.info(f"🚀 Bot Webhook o'rnatildi: {webhook_url}")
    yield
    # Server o'chganda sessionni yopish
    await main_bot.session.close()

app = FastAPI(lifespan=lifespan)
logging.basicConfig(level=logging.INFO)

# --- STATES ---
class BuildForm(StatesGroup):
    wait_token = State()
    admin_prem = State()

# --- KEYBOARDS ---
def main_kb(user_id):
    btns = [
        [KeyboardButton(text="🤖 Bot yaratish"), KeyboardButton(text="🛠 Mening botlarim")],
        [KeyboardButton(text="💎 Premium olish"), KeyboardButton(text="📊 Statistika")]
    ]
    if user_id == ADMIN_ID:
        btns.append([KeyboardButton(text="👑 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(message: types.Message):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", 
                 (message.from_user.id, message.from_user.username))
    conn.commit()
    conn.close()
    await message.answer(f"Salom {message.from_user.first_name}! Bo'limni tanlang:", reply_markup=main_kb(message.from_user.id))

@dp.message(F.text == "🤖 Bot yaratish")
async def create_bot(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    conn = get_db()
    res = conn.execute("SELECT is_premium FROM users WHERE user_id=?", (user_id,)).fetchone()
    is_prem = res[0] if res else 0
    count = conn.execute("SELECT COUNT(*) FROM bots WHERE owner_id=?", (user_id,)).fetchone()[0]
    conn.close()

    if count >= 1 and not is_prem:
        await message.answer("❌ Bepul limit (1 ta bot) tugagan. Premium oling yoki botni o'chiring.\nPremium uchun: @Sardorbeko008")
        return

    btns = [
        [InlineKeyboardButton(text="🎬 Kino Bot", callback_data="type_kino")],
        [InlineKeyboardButton(text="📈 Nakrutka Bot", callback_data="type_nakrutka")]
    ]
    await message.answer("Qaysi turdagi botni yaratmoqchisiz?", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data.startswith("type_"))
async def ask_token(callback: types.CallbackQuery, state: FSMContext):
    b_type = callback.data.split("_")[1]
    await state.update_data(b_type=b_type)
    await state.set_state(BuildForm.wait_token)
    await callback.message.answer(f"Tanlandi: {b_type}. Endi API Tokenni yuboring:")
    await callback.answer()

@dp.message(BuildForm.wait_token)
async def save_bot(message: types.Message, state: FSMContext):
    token = message.text.strip()
    data = await state.get_data()
    b_type = data.get('b_type')
    
    try:
        # Yangi botni tekshirish va unga webhook o'rnatish
        new_bot = Bot(token=token)
        webhook_url = f"https://{WEBHOOK_DOMAIN}/webhook/{token}"
        await new_bot.set_webhook(url=webhook_url)
        
        conn = get_db()
        conn.execute("INSERT OR REPLACE INTO bots (bot_token, owner_id, type) VALUES (?,?,?)", 
                     (token, message.from_user.id, b_type))
        conn.commit()
        conn.close()
        
        await message.answer(f"✅ Tabriklaymiz! {b_type} botingiz ishga tushdi!", reply_markup=main_kb(message.from_user.id))
        await state.clear()
        await new_bot.session.close()
    except:
        await message.answer("❌ Xato! Token noto'g'ri yoki bot allaqachon boshqa joyda ishlayapti.")

# --- ADMIN PANEL ---
@dp.message(F.text == "👑 Admin Panel", F.from_user.id == ADMIN_ID)
async def admin(message: types.Message):
    btns = [[InlineKeyboardButton(text="➕ Premium berish", callback_data="give_prem")]]
    await message.answer("Admin Panel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data == "give_prem")
async def prem_id(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BuildForm.admin_prem)
    await callback.message.answer("Premium beriladigan foydalanuvchi ID sini yuboring:")
    await callback.answer()

@dp.message(BuildForm.admin_prem)
async def give_prem_final(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        target_id = int(message.text)
        conn = get_db()
        conn.execute("UPDATE users SET is_premium=1 WHERE user_id=?", (target_id,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ ID: {target_id} foydalanuvchiga Premium berildi!")
        try:
            await main_bot.send_message(target_id, "🎉 Tabriklaymiz! Sizga Premium statusi berildi.")
        except: pass
        await state.clear()
    else:
        await message.answer("❌ Faqat raqamlardan iborat ID kiriting.")

# --- WEBHOOK ENDPOINTS ---
@app.post("/main-webhook")
async def main_bot_webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(main_bot, update)
    return {"ok": True}

@app.post("/webhook/{token}")
async def user_bot_webhook(token: str, request: Request):
    data = await request.json()
    conn = get_db()
    res = conn.execute("SELECT type FROM bots WHERE bot_token=?", (token,)).fetchone()
    conn.close()
    
    if res:
        b_type = res[0]
        bot = Bot(token=token)
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            if b_type == "type_kino":
                await bot.send_message(chat_id, "🎬 Kino botingizga xush kelibsiz! Kodni yuboring.")
            else:
                await bot.send_message(chat_id, "📈 Nakrutka xizmati faol!")
        await bot.session.close()
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
