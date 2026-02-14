import asyncio
import random
import aiosqlite
import pandas as pd
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

BOT_TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

DB_NAME = "database.db"


# ---------------- DATABASE ----------------

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            ref_by INTEGER,
            ref_count INTEGER DEFAULT 0,
            joined_at TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT
        )
        """)
        await db.commit()


# ---------------- START WITH REF ----------------

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    args = message.get_args()
    ref_by = None

    if args:
        try:
            ref_by = int(args)
        except:
            pass

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id=?", (message.from_user.id,)) as c:
            exists = await c.fetchone()

        if not exists:
            await db.execute(
                "INSERT INTO users VALUES (?, ?, ?, 0, ?)",
                (
                    message.from_user.id,
                    message.from_user.username,
                    ref_by,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

            if ref_by:
                await db.execute(
                    "UPDATE users SET ref_count = ref_count + 1 WHERE user_id=?",
                    (ref_by,)
                )

        await db.commit()

    link = f"https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}"

    await message.answer(
        f"🎉 Konkursga qo‘shildingiz!\n\n"
        f"👥 Siz taklif qilganlar: tekshirilmoqda...\n\n"
        f"🔗 Referal link:\n{link}"
    )


# ---------------- STATS ----------------

@dp.message_handler(commands=["stats"])
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            total = await c.fetchone()

    await message.answer(f"👥 Jami qatnashchilar: {total[0]}")


# ---------------- WEIGHTED WINNER ----------------

@dp.message_handler(commands=["winner"])
async def winner(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        count = int(message.get_args())
    except:
        await message.answer("Misol: /winner 3")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id, username, ref_count FROM users"
        ) as cursor:
            users = await cursor.fetchall()

    weighted_list = []

    for user_id, username, ref_count in users:
        weight = ref_count + 1
        weighted_list.extend([(user_id, username)] * weight)

    if len(weighted_list) < count:
        await message.answer("Yetarli odam yo‘q!")
        return

    winners = random.sample(weighted_list, count)

    text = "🏆 G‘oliblar:\n\n"
    for user_id, username in winners:
        if username:
            text += f"@{username}\n"
        else:
            text += f"[User](tg://user?id={user_id})\n"

    await message.answer(text, parse_mode="Markdown")


# ---------------- EXCEL EXPORT ----------------

@dp.message_handler(commands=["export"])
async def export_excel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users") as cursor:
            data = await cursor.fetchall()

    df = pd.DataFrame(data, columns=["user_id", "username", "ref_by", "ref_count", "joined_at"])
    file_name = "participants.xlsx"
    df.to_excel(file_name, index=False)

    await message.answer_document(open(file_name, "rb"))
    

# ---------------- STARTUP ----------------

async def on_startup(dp):
    await init_db()
    print("GOD LEVEL BOT ishga tushdi")


if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)
