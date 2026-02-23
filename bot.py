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

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect("bot_builder.db")
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

# --- ICHKI BOTLAR UCHUN LOGIKA ---
async def run_sub_bot(token, b_type, owner_id):
    """Har bir foydalanuvchi botini alohida ishga tushirish"""
    try:
        sub_bot = Bot(token=token, parse_mode="HTML")
        sub_dp = Dispatcher(sub_bot)

        @sub_dp.message_handler(commands=['start'])
        async def sub_start(message: types.Message):
            if b_type == 'kino':
                await message.answer("🎬 <b>Kino Bot faol!</b>\nKino kodini kiriting:")
            elif b_type == 'nakrutka':
                await message.answer("🚀 <b>Nakrutka Bot faol!</b>\nXizmatlar ro'yxati: /services")
            else:
                await message.answer("💰 <b>Pul ishlash boti!</b>\nDo'stlarni taklif qiling.")
            
            if message.from_user.id == owner_id:
                await message.answer("🛠 <b>Admin Panel:</b> /admin_panel")

        logging.info(f"Bot ishga tushdi: {token[:10]}")
        await sub_dp.start_polling()
    except Exception as e:
        logging.error(f"Botda xatolik ({token[:5]}): {e}")

# --- ASOSIY BUILDER BOT BUYRUQLARI ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    conn = sqlite3.connect("bot_builder.db")
    cur = conn.cursor()
    
    # Foydalanuvchini ro'yxatga olish
    expire_time = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute("INSERT OR IGNORE INTO users (user_id, expire_date) VALUES (?, ?)", (uid, expire_time))
    cur.execute("SELECT status, expire_date, is_premium FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    conn.commit()
    conn.close()

    # Muddatni tekshirish
    expire_dt = datetime.strptime(user[1], '%Y-%m-%d %H:%M:%S')
    if expire_dt < datetime.now():
        await message.answer(f"❌ <b>Vaqt tugadi!</b>\nTo'lov: <code>{CARD_NUMBER}</code>\nAdmin: @Sardorbeko008")
        return

    status_name = "Premium 💎" if user[2] == 1 else "Bepul 🆓"
    await message.answer(
        f"🛠 <b>Builder Botga xush kelibsiz!</b>\n\n"
        f"Holatingiz: {status_name}\n"
        f"Muddat: {user[1]}\n\n"
        f"Yangi bot ochish uchun /new_bot buyrug'ini bering."
    )

@dp.message_handler(commands=['premium_ber'], user_id=ADMIN_ID)
async def give_premium(message: types.Message):
    try:
        target_id = int(message.get_args())
        expire = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect("bot_builder.db")
        cur = conn.cursor()
        cur.execute("UPDATE users SET status='premium', is_premium=1, expire_date=? WHERE user_id=?", (expire, target_id))
        conn.commit()
        conn.close()
        await message.answer(f"✅ {target_id} ga 30 kunlik Premium berildi.")
        await main_bot.send_message(target_id, "💎 Tabriklaymiz! Sizga Premium berildi (5 ta bot limiti).")
    except:
        await message.answer("Xato! Foydalanuvchi ID raqamini kiriting.")

@dp.message_handler(commands=['new_bot'])
async def create_new(message: types.Message):
    await message.answer("🤖 Bot <b>TOKEN</b>ini yuboring:")
    await Form.waiting_for_token.set()

@dp.message_handler(state=Form.waiting_for_token)
async def get_token(message: types.Message, state: FSMContext):
    if ":" not in message.text:
        await message.answer("Token noto'g'ri. BotFather dan olingan to'g'ri tokenni yuboring.")
        return
    await state.update_data(token=message.text)
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("🎬 Kino Bot", "🚀 Nakrutka Bot", "💰 Pul ishlash Bot")
    await message.answer("Bot turini tanlang:", reply_markup=kb)
    await Form.next()

@dp.message_handler(state=Form.choosing_type)
async def finalize_bot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    b_type = 'kino' if "Kino" in message.text else 'nakrutka' if "Nakrutka" in message.text else 'money'
    
    try:
        conn = sqlite3.connect("bot_builder.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO bots (owner_id, token, type) VALUES (?, ?, ?)", 
                    (message.from_user.id, data['token'], b_type))
        conn.commit()
        conn.close()
        
        await message.answer("✅ Bot muvaffaqiyatli qo'shildi!", reply_markup=types.ReplyKeyboardRemove())
        # Botni orqa fonda ishga tushirish
        asyncio.create_task(run_sub_bot(data['token'], b_type, message.from_user.id))
    except sqlite3.IntegrityError:
        await message.answer("❌ Bu bot allaqachon tizimga qo'shilgan.")
    
    await state.finish()

# --- STARTUP: Barcha botlarni yoqish ---
async def on_startup(dp):
    init_db()
    conn = sqlite3.connect("bot_builder.db")
    cur = conn.cursor()
    cur.execute("SELECT token, type, owner_id FROM bots")
    all_bots = cur.fetchall()
    conn.close()
    
    for b in all_bots:
        asyncio.create_task(run_sub_bot(b[0], b[1], b[2]))

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
