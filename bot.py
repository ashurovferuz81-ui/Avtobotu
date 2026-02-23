import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from factory import run_factory_bot

MASTER_TOKEN = "8511690084:AAE5bCLOO3rXwsZQNJ3JjjSmNxL-4MMlG80"
ADMIN_ID = 5775388579

class BuildStates(StatesGroup):
    choosing_type = State()
    waiting_token = State()

bot = Bot(token=MASTER_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎬 Kino Bot", callback_data="type_kino")],
        [types.InlineKeyboardButton(text="📈 Nakrutka Bot", callback_data="type_nakrutka")],
        [types.InlineKeyboardButton(text="🤫 Anonim Chat", callback_data="type_anonim")],
        [types.InlineKeyboardButton(text="📿 Zikr Bot", callback_data="type_zikr")],
        [types.InlineKeyboardButton(text="🎵 Musiqa Bot", callback_data="type_musiqa")],
        [types.InlineKeyboardButton(text="💎 Ismlar Ma'nosi", callback_data="type_ismlar")]
    ]) # Shunday qilib 15 tagacha qo'shish mumkin
    await m.answer("🚀 **Bot Fabrikasiga xush kelibsiz!**\nQaysi botni ochamiz?", reply_markup=kb)

@dp.callback_query(F.data.startswith("type_"))
async def set_type(c: types.CallbackQuery, state: FSMContext):
    b_type = c.data.split("_")[1]
    await state.update_data(chosen_type=b_type)
    await c.message.answer(f"✅ {b_type.upper()} tanlandi. Endi @BotFather dan olgan tokenni yuboring:")
    await state.set_state(BuildStates.waiting_token)

@dp.message(BuildStates.waiting_token, F.text.contains(":"))
async def save_bot(m: types.Message, state: FSMContext):
    data = await state.get_data()
    b_type = data['chosen_type']
    token = m.text.strip()
    
    async with db.pool.acquire() as conn:
        await conn.execute("INSERT INTO my_bots (owner_id, token, bot_type) VALUES ($1, $2, $3) ON CONFLICT (owner_id) DO UPDATE SET token=$2, bot_type=$3",
                           m.from_user.id, token, b_type)
    
    asyncio.create_task(run_factory_bot(token, b_type, m.from_user.id))
    await m.answer(f"🎊 Tabriklaymiz! Sizning {b_type} botingiz ishga tushdi.")
    await state.clear()

async def main():
    await db.connect()
    # Railway o'chib yonganda barcha botlarni qayta ishga tushirish
    async with db.pool.acquire() as conn:
        rows = await conn.fetch("SELECT token, bot_type, owner_id FROM my_bots")
        for row in rows:
            asyncio.create_task(run_factory_bot(row['token'], row['bot_type'], row['owner_id']))
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
