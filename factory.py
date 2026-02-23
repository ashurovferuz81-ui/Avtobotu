from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from database import db

async def run_factory_bot(token, bot_type, owner_id):
    bot = Bot(token=token)
    dp = Dispatcher()

    # --- 1. KINO BOT ---
    if bot_type == "kino":
        @dp.message(F.video, F.from_user.id == owner_id)
        async def add_kino(m: types.Message):
            async with db.pool.acquire() as conn:
                await conn.execute("INSERT INTO bot_content VALUES ($1, $2, $3)", token, m.caption, m.video.file_id)
            await m.answer(f"✅ Kino saqlandi: {m.caption}")

    # --- 2. NAKRUTKA BOT ---
    elif bot_type == "nakrutka":
        @dp.message(Command("start"))
        async def nakrutka(m: types.Message):
            await m.answer("📈 Nakrutka xizmatlari:\n1. TG Obunachi - 10k\n2. Insta Like - 5k\nAdmin: @Sardorbeko008")

    # --- 3. ANONIM CHAT ---
    elif bot_type == "anonim":
        @dp.message(Command("start"))
        async def anon(m: types.Message):
            await m.answer("🤫 Anonim chatga xush kelibsiz! Tezak orada sherik topamiz...")

    # --- 4. ZIKR BOT ---
    elif bot_type == "zikr":
        @dp.message(Command("start"))
        async def zikr(m: types.Message):
            await m.answer("📿 Subhanalloh, Alhamdu lillah, Allohu Akbar.")

    # --- 5. VALYUTA ---
    elif bot_type == "valyuta":
        @dp.message(Command("start"))
        async def money(m: types.Message):
            await m.answer("💵 USD: 12,850 so'm\n💶 EUR: 13,900 so'm")

    # --- 6. ISMLAR MA'NOSI ---
    elif bot_type == "ismlar":
        @dp.message(F.text)
        async def name_mean(m: types.Message):
            await m.answer(f"✨ {m.text} ismining ma'nosi: 'Yaxshilik va nur' deganidir.")

    # --- 7. MUSIQA BOT ---
    elif bot_type == "musiqa":
        @dp.message(F.audio, F.from_user.id == owner_id)
        async def add_music(m: types.Message):
            async with db.pool.acquire() as conn:
                await conn.execute("INSERT INTO bot_content VALUES ($1, $2, $3)", token, m.caption, m.audio.file_id)
            await m.answer("🎵 Musiqa bazaga qo'shildi!")

    # --- 8-15 TURLAR (QOLGANLARI UCHUN DEFAULT JAVOB) ---
    else:
        @dp.message(Command("start"))
        async def other(m: types.Message):
            await m.answer(f"🤖 Sizning {bot_type} botingiz ishga tushdi!")

    # UMUMIY QIDIRISH (Kino va Musiqa uchun)
    @dp.message(F.text.isdigit())
    async def search(m: types.Message):
        async with db.pool.acquire() as conn:
            res = await conn.fetchrow("SELECT file_id FROM bot_content WHERE bot_token=$1 AND key_val=$2", token, m.text)
        if res:
            if bot_type == "kino": await m.answer_video(res['file_id'])
            elif bot_type == "musiqa": await m.answer_audio(res['file_id'])

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
