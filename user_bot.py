from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite

class BotStates(StatesGroup):
    add_code = State()
    add_video = State()
    del_code = State()
    set_channel = State()

async def run_user_bot(token, owner_id):
    bot = Bot(token=token)
    dp = Dispatcher()

    def get_admin_kb():
        return types.ReplyKeyboardMarkup(keyboard=[
            [types.KeyboardButton(text="🎬 Kino qo'shish"), types.KeyboardButton(text="🗑 Kino o'chirish")],
            [types.KeyboardButton(text="📢 Kanal sozlash"), types.KeyboardButton(text="❌ Kanalni o'chirish")],
            [types.KeyboardButton(text="📊 Statistika")]
        ], resize_keyboard=True)

    @dp.message(Command("start"))
    async def u_start(m: types.Message, state: FSMContext):
        await state.clear()
        async with aiosqlite.connect("kino_system.db") as db:
            cursor = await db.execute("SELECT sub_channel FROM my_bots WHERE token=?", (token,))
            res = await cursor.fetchone()
            channel = res[0]

        if m.from_user.id == owner_id:
            await m.answer("🛠 Bot boshqaruv paneli:", reply_markup=get_admin_kb())
        else:
            # Majburiy obuna tekshiruvi
            if channel:
                try:
                    chat_member = await bot.get_chat_member(chat_id=channel, user_id=m.from_user.id)
                    if chat_member.status in ["left", "kicked"]:
                        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{channel[1:]}")]])
                        return await m.answer(f"Botdan foydalanish uchun {channel} kanaliga a'zo bo'ling!", reply_markup=kb)
                except: pass
            await m.answer("🎬 Kino kodini yuboring:")

    # --- KINO QO'SHISH ---
    @dp.message(F.text == "🎬 Kino qo'shish", F.from_user.id == owner_id)
    async def u_add(m: types.Message, state: FSMContext):
        await m.answer("Kino kodini yozing:")
        await state.set_state(BotStates.add_code)

    @dp.message(BotStates.add_code)
    async def u_code(m: types.Message, state: FSMContext):
        await state.update_data(code=m.text)
        await m.answer("Endi videoni yuboring:")
        await state.set_state(BotStates.add_video)

    @dp.message(BotStates.add_video, F.video)
    async def u_video(m: types.Message, state: FSMContext):
        data = await state.get_data()
        async with aiosqlite.connect("kino_system.db") as db:
            await db.execute("INSERT INTO movies VALUES (?, ?, ?)", (token, data['code'], m.video.file_id))
            await db.commit()
        await m.answer(f"✅ Saqlandi! Kod: {data['code']}")
        await state.clear()

    # --- KANAL SOZLASH ---
    @dp.message(F.text == "📢 Kanal sozlash", F.from_user.id == owner_id)
    async def u_chan(m: types.Message, state: FSMContext):
        await m.answer("Kanal username yuboring (Masalan: @sizning_kanalingiz):\n*Bot kanalda admin bo'lishi shart!*")
        await state.set_state(BotStates.set_channel)

    @dp.message(BotStates.set_channel)
    async def u_chan_save(m: types.Message, state: FSMContext):
        if m.text.startswith("@"):
            async with aiosqlite.connect("kino_system.db") as db:
                await db.execute("UPDATE my_bots SET sub_channel=? WHERE token=?", (m.text, token))
                await db.commit()
            await m.answer(f"✅ Kanal saqlandi: {m.text}")
            await state.clear()
        else: await m.answer("❌ Xato! Username @ bilan boshlanishi kerak.")

    @dp.message(F.text == "❌ Kanalni o'chirish", F.from_user.id == owner_id)
    async def u_chan_del(m: types.Message):
        async with aiosqlite.connect("kino_system.db") as db:
            await db.execute("UPDATE my_bots SET sub_channel=NULL WHERE token=?", (token,))
            await db.commit()
        await m.answer("✅ Majburiy obuna olib tashlandi.")

    # --- STATISTIKA ---
    @dp.message(F.text == "📊 Statistika", F.from_user.id == owner_id)
    async def u_stats(m: types.Message):
        async with aiosqlite.connect("kino_system.db") as db:
            cur = await db.execute("SELECT COUNT(*) FROM movies WHERE bot_token=?", (token,))
            count = await cur.fetchone()
        await m.answer(f"📊 Botingizdagi jami kinolar soni: {count[0]} ta")

    # --- KINO QIDIRISH ---
    @dp.message(F.text)
    async def u_search(m: types.Message):
        async with aiosqlite.connect("kino_system.db") as db:
            cur = await db.execute("SELECT file_id FROM movies WHERE bot_token=? AND code=?", (token, m.text))
            res = await cur.fetchone()
        if res: await m.answer_video(res[0], caption=f"🎬 Kod: {m.text}")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
