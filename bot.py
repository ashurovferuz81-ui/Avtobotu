import os
import logging
import asyncio
import psycopg2
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
DB_URL = os.getenv("DATABASE_URL")
CARD_NUMBER = "8600 1234 5678 9012"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

class Form(StatesGroup):
    waiting_for_token = State()
    choosing_type = State()

# --- DATABASE ---
def get_db_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS builder_users (
        user_id BIGINT PRIMARY KEY,
        status TEXT DEFAULT 'free',
        expire_date TIMESTAMP,
        is_premium BOOLEAN DEFAULT FALSE
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS sub_bots (
        id SERIAL PRIMARY KEY,
        owner_id BIGINT,
        bot_token TEXT UNIQUE,
        bot_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    cur.close()
    conn.close()

# --- MULTI-BOT MANTIG'I (HAR BIR BOT UCHUN ALOHIDA) ---
async def start_sub_bot(token, b_type, owner_id):
    try:
        s_bot = Bot(token=token, parse_mode="HTML")
        s_dp = Dispatcher(s_bot)

        # 1. KINO BOT FUNKSIYALARI
        if b_type == 'kino':
            @s_dp.message_handler(commands=['start'])
            async def k_start(m: types.Message):
                await m.answer("🎬 <b>Kino Botga xush kelibsiz!</b>\nKino kodini kiriting:")
                if m.from_user.id == owner_id:
                    await m.answer("🛠 <b>Admin Panel:</b> /add_kino, /stats")

        # 2. NAKRUTKA BOT FUNKSIYALARI
        elif b_type == 'nakrutka':
            @s_dp.message_handler(commands=['start'])
            async def n_start(m: types.Message):
                await m.answer("🚀 <b>Nakrutka Bot!</b>\nNarxlar: 1k obuna - 5000 so'm.\nBuyurtma berish uchun /order")

        # 3. PUL ISHLA BOT FUNKSIYALARI
        elif b_type == 'money':
            @s_dp.message_handler(commands=['start'])
            async def p_start(m: types.Message):
                link = f"https://t.me/{(await s_bot.get_me()).username}?start={m.from_user.id}"
                await m.answer(f"💰 <b>Har bir taklif uchun 500 so'm!</b>\nSizning havolangiz: {link}")

        logging.info(f"Bot yoqildi: {token[:10]}")
        await s_dp.start_polling()
    except Exception as e:
        logging.error(f"Xato botda {token[:5]}: {e}")

# --- BUILDER ADMIN BUYRUQLARI ---
@dp.message_handler(commands=['premium_ber'], user_id=ADMIN_ID)
async def give_prem(message: types.Message):
    target = int(message.get_args())
    expire = datetime.now() + timedelta(days=30)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE builder_users SET status='premium', is_premium=TRUE, expire_date=%s WHERE user_id=%s", (expire, target))
    conn.commit()
    cur.close()
    conn.close()
    await message.answer("✅ Premium 1 oyga berildi.")
    await bot.send_message(target, "💎 Tabriklaymiz! Sizga 1 oylik Premium berildi.")

# --- FOYDALANUVCHI STARTI ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    uid = message.from_user.id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO builder_users (user_id, expire_date) VALUES (%s, %s) ON CONFLICT DO NOTHING", 
                (uid, datetime.now() + timedelta(days=7)))
    cur.execute("SELECT status, expire_date, is_premium FROM builder_users WHERE user_id=%s", (uid,))
    user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if user[1] < datetime.now():
        await message.answer(f"❌ <b>Bot vaqti tugadi!</b>\n\nTo'lov uchun: <code>{CARD_NUMBER}</code>\nAdmin: @Sardorbeko008")
        return

    await message.answer(f"🛠 <b>Builder Bot</b>\nHolat: {user[0]}\n\nBot yaratish: /new_bot")

@dp.message_handler(commands=['new_bot'])
async def new_bot(message: types.Message):
    await message.answer("🤖 Bot <b>TOKEN</b>ini yuboring:")
    await Form.waiting_for_token.set()

@dp.message_handler(state=Form.waiting_for_token)
async def get_token(message: types.Message, state: FSMContext):
    await state.update_data(token=message.text)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎬 Kino", "🚀 Nakrutka", "💰 Pul ishlash")
    await message.answer("Bot turini tanlang:", reply_markup=kb)
    await Form.next()

@dp.message_handler(state=Form.choosing_type)
async def set_type(message: types.Message, state: FSMContext):
    data = await state.get_data()
    b_type = 'kino' if "Kino" in message.text else 'nakrutka' if "Nakrutka" in message.text else 'money'
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO sub_bots (owner_id, bot_token, bot_type) VALUES (%s, %s, %s)", 
                (message.from_user.id, data['token'], b_type))
    conn.commit()
    cur.close()
    conn.close()

    await message.answer("✅ Bot muvaffaqiyatli yaratildi va yoqildi!", reply_markup=types.ReplyKeyboardRemove())
    asyncio.create_task(start_sub_bot(data['token'], b_type, message.from_user.id))
    await state.finish()

if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)
