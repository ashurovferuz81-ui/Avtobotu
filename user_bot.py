from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite

class KinoStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_video = State()
    waiting_for_del_code = State()

async def start_user_bot(token, owner_id):
    bot = Bot(token=token)
    dp = Dispatcher()

    # --- ADMIN KEYBOARD ---
    def get_admin_kb():
        return types.ReplyKeyboardMarkup(keyboard=[
            [types.KeyboardButton(text="🎬 Kino qo'shish"), types.KeyboardButton(text="🗑 Kino o'chirish")],
            [types.KeyboardButton(text="📊 Statistika")]
        ], resize_keyboard=True)

    @dp.message(Command("start"))
    async def u_start(m: types.Message, state: FSMContext):
        await state.clear()
        if m.from_user.id == owner_id:
            await m.answer("👋 Admin panelga xush kelibsiz!", reply_markup=get_admin_kb())
        else:
            await m.answer("🎬 Kino kodini yuboring:")

    # --- KINO QO'SHISH ---
    @dp.message(F.text == "🎬 Kino qo'shish", F.from_user.id == owner_id)
    async def u_add(m: types.Message, state: FSMContext):
        await m.answer("Kino uchun kod yuboring (Faqat raqam):")
        await state.set_state(KinoStates.waiting_for_code)

    @dp.message(KinoStates.waiting_for_code)
    async def u_code(m: types.Message, state: FSMContext):
        if m.text.isdigit():
            await state.update_data(m_code=m.text)
            await m.answer("Endi kinoni VIDEO qilib yuboring:")
            await state.set_state(KinoStates.waiting_for_video)
        else:
            await m.answer("Iltimos, faqat raqam yuboring!")

    @dp.message(KinoStates.waiting_for_video, F.video)
    async def u_video(m: types.Message, state: FSMContext):
        data = await state.get_data()
        async with aiosqlite.connect("kino_bot.db") as db:
            await db.execute("INSERT INTO movies VALUES (?, ?, ?)", (token, data['m_code'], m.video.file_id))
            await db.commit()
        await m.answer(f"✅ Kino saqlandi! Kod: {data['m_code']}")
        await state.clear()

    # --- KINO O'CHIRISH ---
    @dp.message(F.text == "🗑 Kino o'chirish", F.from_user.id == owner_id)
    async def u_del(m: types.Message, state: FSMContext):
        await m.answer("O'chirmoqchi bo'lgan kino kodini yuboring:")
        await state.set_state(KinoStates.waiting_for_del_code)

    @dp.message(KinoStates.waiting_for_del_code)
    async def u_del_conf(m: types.Message, state: FSMContext):
        async with aiosqlite.connect("kino_bot.db") as db:
            await db.execute("DELETE FROM movies WHERE bot_token=? AND code=?", (token, m.text))
            await db.commit()
        await m.answer(f"🗑 Kod {m.text} o'chirildi.")
        await state.clear()

    # --- KINO QIDIRISH ---
    @dp.message(F.text.isdigit())
    async def u_search(m: types.Message):
        async with aiosqlite.connect("kino_bot.db") as db:
            cursor = await db.execute("SELECT file_id FROM movies WHERE bot_token=? AND code=?", (token, m.text))
            movie = await cursor.fetchone()
            if movie:
                await m.answer_video(movie[0], caption=f"🎬 Kod: {m.text}")
            else:
                await m.answer("❌ Kino topilmadi.")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Bot error: {e}")
