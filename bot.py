import asyncio
import random
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ---------------- CONFIG ----------------
BOT_TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

DB_NAME = "database.db"
contest_open = True


# ---------------- DATABASE INIT ----------------
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Foydalanuvchilar
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_active INTEGER DEFAULT 1
        )
        """)
        # Kanal
        await db.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT
        )
        """)
        # G'oliblar
        await db.execute("""
        CREATE TABLE IF NOT EXISTS winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            won_at TEXT
        )
        """)
        await db.commit()


# ---------------- OBUNA TEKSHIRISH ----------------
async def check_subscriptions(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT channel_id FROM channels") as cursor:
            channels = await cursor.fetchall()

    for channel in channels:
        try:
            member = await bot.get_chat_member(channel[0], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True


# ---------------- START COMMAND ----------------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    global contest_open

    if not contest_open:
        await message.answer("❌ Konkurs yopilgan")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT channel_id FROM channels") as c:
            channels = await c.fetchall()

    if not channels:
        await message.answer("Konkurs hali sozlanmagan")
        return

    keyboard = InlineKeyboardMarkup()
    for ch in channels:
        keyboard.add(
            InlineKeyboardButton(
                text=f"📢 {ch[0]}",
                url=f"https://t.me/{ch[0].replace('@','')}"
            )
        )
    keyboard.add(
        InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")
    )

    await message.answer("Majburiy kanallarga obuna bo‘ling:", reply_markup=keyboard)


# ---------------- TEKSHIRISH ----------------
@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_sub(call: types.CallbackQuery):
    is_sub = await check_subscriptions(call.from_user.id)

    if not is_sub:
        await call.answer("❌ Obuna to‘liq emas!", show_alert=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, username, is_active) VALUES (?, ?, 1)",
            (call.from_user.id, call.from_user.username)
        )
        await db.commit()

    await call.message.edit_text("🎉 Konkursga muvaffaqiyatli qo‘shildingiz!")
    await call.answer()


# ---------------- ADMIN: ADD CHANNEL ----------------
@dp.message_handler(commands=["addchannel"])
async def add_channel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    channel = message.get_args()
    if not channel:
        await message.answer("Misol: /addchannel @kanal")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO channels (channel_id) VALUES (?)", (channel,))
        await db.commit()

    await message.answer("✅ Kanal qo‘shildi")


# ---------------- ADMIN: CLOSE / OPEN ----------------
@dp.message_handler(commands=["close"])
async def close_contest(message: types.Message):
    global contest_open
    if message.from_user.id != ADMIN_ID:
        return
    contest_open = False
    await message.answer("🔒 Konkurs yopildi")


@dp.message_handler(commands=["open"])
async def open_contest(message: types.Message):
    global contest_open
    if message.from_user.id != ADMIN_ID:
        return
    contest_open = True
    await message.answer("🔓 Konkurs ochildi")


# ---------------- WINNER WITH ANIMATION ----------------
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
        async with db.execute("""
            SELECT user_id, username FROM users
            WHERE is_active=1
            AND user_id NOT IN (SELECT user_id FROM winners)
        """) as c:
            users = await c.fetchall()

    if len(users) < count:
        await message.answer("Yetarli odam yo‘q")
        return

    msg = await message.answer("🎰 G‘olib aniqlanmoqda...")

    for i in range(5):
        await asyncio.sleep(0.5)
        fake = random.choice(users)
        await msg.edit_text(f"🎰 Tanlanmoqda...\n@{fake[1]}")

    winners = random.sample(users, count)

    async with aiosqlite.connect(DB_NAME) as db:
        for user_id, username in winners:
            await db.execute(
                "INSERT INTO winners (user_id, username, won_at) VALUES (?, ?, ?)",
                (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
        await db.commit()

    text = "🏆 G‘oliblar:\n\n"
    for _, username in winners:
        text += f"@{username}\n"

    await msg.edit_text(text)


# ---------------- STARTUP ----------------
async def on_startup(dp):
    await init_db()
    print("NEXT LVL 3 BOT ishga tushdi")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
