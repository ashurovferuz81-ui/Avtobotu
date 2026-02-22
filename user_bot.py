from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from database import db

class UserBotInstance:
    def __init__(self, token, owner_id):
        self.token = token
        self.owner_id = owner_id
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.setup_handlers()

    def setup_handlers(self):
        @self.dp.message(Command("start"))
        async def start(m: types.Message):
            if m.from_user.id == self.owner_id:
                kb = types.ReplyKeyboardMarkup(keyboard=[
                    [types.KeyboardButton(text="➕ Kino qo'shish"), types.KeyboardButton(text="🗑 O'chirish")]
                ], resize_keyboard=True)
                await m.answer("👑 Admin panel:", reply_markup=kb)
            else:
                await m.answer("🎬 Kino kodini yuboring:")

        @self.dp.message(F.video, F.from_user.id == self.owner_id)
        async def add_movie(m: types.Message):
            if m.caption and m.caption.isdigit():
                db.cur.execute("INSERT OR REPLACE INTO movies VALUES (?, ?, ?)", (self.token, m.caption, m.video.file_id))
                db.conn.commit()
                await m.answer(f"✅ Saqlandi: {m.caption}")

        @self.dp.message(F.text.isdigit())
        async def search(m: types.Message):
            res = db.cur.execute("SELECT file_id FROM movies WHERE bot_token=? AND code=?", (self.token, m.text)).fetchone()
            if res:
                await m.answer_video(res[0], caption=f"Kod: {m.text}")
            else:
                await m.answer("❌ Topilmadi")

    async def start(self):
        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            await self.dp.start_polling(self.bot)
        except Exception as e:
            print(f"Xato: {self.token[:10]} - {e}")
