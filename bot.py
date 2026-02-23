import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# --- SOZLAMALAR ---
BUILDER_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
CARD_NUMBER = "8600 1234 5678 9012"

logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
main_bot = Bot(token=BUILDER_TOKEN, parse_mode="HTML")
dp = Dispatcher(main_bot, storage=storage)

class Form(StatesGroup):
    waiting_for_token = State()
    choosing_type = State()

# --- SQLITE DATABASE ---
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        status TEXT DEFAULT 'free',
        expire_date TEXT,
        is_premium INTEGER DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS bots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER,
        token TEXT UNIQUE,
        type TEXT
    )""")
    conn.commit()
    conn.close()

# --- MULTI-BOT MANTIG'I ---
async def start_sub_bot(token, b_type, owner_id):
    try:
        s_bot = Bot(token=token, parse_mode="HTML")
        s_dp = Dispatcher(s_bot)

        @s_dp.message_handler(commands=['start'])
        async def sub_start(m: types.Message):
            if b_type == 'kino':
                await m.answer("🎬 <b>Kino Bot faol!</b>\nKino kodini kiriting:")
            elif b_type == 'nakrutka':
                await m.answer("🚀 <b>Nakrutka Bot faol!</b>\nNarxlar: 1k - 5000 so'm.")
            else:
                await m.answer("💰 <b>Pul ishlash boti!</b>\nDo'stlarni taklif qiling.")
            
            if m.from_user.id == owner_id:
                await m.answer("🛠 <b>Bot egasi uchun panel:</b> /admin")

        logging.info(f"Bot yoqildi: {token[:10]}")
        await s_dp.start_polling()
    except Exception as e:
        logging.error(f"Xato: {e}")

# --- BUILDER ADMIN BUYRUQLARI ---
@dp.message_handler(commands=['premium_ber'], user_id=ADMIN_ID)
async def give_prem(message: types.Message):
    try:
        target = int(message.get_args())
        expire = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("UPDATE users SET status='premium', is_premium=1, expire_date=? WHERE user_id=?", (expire, target))
        conn.commit()
        conn.close()
        await message.answer(f"✅ {target} ga Premium berildi.")
        await main_bot.send_message(target, "💎 Premium berildi! Endi 5 ta bot ochishingiz mumkin.")
    except: await message.answer("ID xato.")

# --- START VA NEW BOT ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    uid = message.from_user.id
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, expire_date) VALUES (?, ?)", 
                (uid, (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')))
    cur.execute("SELECT status, expire_date, is_premium FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    conn.close()

    expire_dt = datetime.strptime(user[1], '%Y-%m-%d %H:%M:%S')
    if expire_dt < datetime.now():
        await message.answer(f"❌ <b>Vaqt tugadi!</b>\nTo'lov: <code>{CARD_NUMBER}</code>\nAdmin: @Sardorbeko008")
        return

    await message.answer(f"🛠 <b>Builder Bot</b>\nHolat: {user[0]}\nMuddat: {user[1]}\n\nBot ochish: /new_bot")

@dp.message_handler(commands=['new_bot'])
async def new_bot(message: types.Message):
    await message.answer("🤖 Bot <b>TOKEN</b>ini yuboring:")
    await Form.waiting_for_token.set()

@dp.message_handler(state=Form.waiting_for_token)
async def get_token(message: types.Message, state: FSMContext):
    if ":" not in message.text:
        await message.answer("Xato token! Qayta yuboring.")
        return
    await state.update_data(token=message.text)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎬 Kino", "🚀 Nakrutka", "💰 Pul ishlash")
    await message.answer("Bot turini tanlang:", reply_markup=kb)
    await Form.next()

@dp.message_handler(state=Form.choosing_type)
async def set_type(message: types.Message, state: FSMContext):
    data = await state.get_data()
    b_type = 'kino' if "Kino" in message.text else 'nakrutka' if "Nakrutka" in message.text else 'money'
    
    try:
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO bots (owner_id, token, type) VALUES (?, ?, ?)", 
                    (message.from_user.id, data['token'], b_type))
        conn.commit()
        conn.close()
        await message.answer("✅ Bot yoqildi!", reply_markup=types.ReplyKeyboardRemove())
        asyncio.create_task(start_sub_bot(data['token'], b_type, message.from_user.id))
    except: await message.answer("Bu bot allaqachon qo'shilgan.")
    await state.finish()

if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)
