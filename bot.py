# bot.py
import os
import asyncio
import asyncpg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ========= ENV =============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "5775388579"))
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:dlWNyapkcvkRlBwgxHpFMvUkRBjBxGKe@postgres.railway.internal:5432/railway")

# ========= DATABASE =============
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    # Userlar
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id BIGINT PRIMARY KEY,
        username TEXT
    )
    """)
    # Kinolar
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS movies(
        code TEXT PRIMARY KEY,
        file_id TEXT,
        name TEXT,
        views BIGINT DEFAULT 0
    )
    """)
    # Kanallar
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS channels(
        channel TEXT PRIMARY KEY
    )
    """)
    await conn.close()

# ========= ADMIN KEYBOARD =========
def admin_keyboard():
    keyboard = [
        ["🎬 Kino qo‘shish", "🗑 Kino o‘chirish"],
        ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
        ["👥 Userlar", "📊 Statistika"],
        ["📣 Broadcast", "🏆 Reytingli kinolar"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========= HELPERS =========
async def add_user(user_id, username):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("INSERT INTO users(user_id, username) VALUES($1,$2) ON CONFLICT DO NOTHING", user_id, username)
    await conn.close()

async def get_all_users():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT user_id, username FROM users")
    await conn.close()
    return rows

async def add_movie(code, file_id, name):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("INSERT INTO movies(code, file_id, name) VALUES($1,$2,$3) ON CONFLICT(code) DO UPDATE SET file_id=$2, name=$3", code, file_id, name)
    await conn.close()

async def del_movie(code):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM movies WHERE code=$1", code)
    await conn.close()

async def get_movie(code):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT file_id,name,views FROM movies WHERE code=$1", code)
    await conn.close()
    return row

async def increase_movie_views(code):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE movies SET views = views + 1 WHERE code=$1", code)
    await conn.close()

async def add_channel(channel):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("INSERT INTO channels(channel) VALUES($1) ON CONFLICT DO NOTHING", channel)
    await conn.close()

async def del_channel(channel):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM channels WHERE channel=$1", channel)
    await conn.close()

async def get_all_channels():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT channel FROM channels")
    await conn.close()
    return [r['channel'] for r in rows]

# ========= CHECK SUB =========
async def not_subscribed(user_id, bot):
    channels = await get_all_channels()
    not_joined = []
    for ch in channels:
        if ch.startswith("@"):  # faqat @ tekshiramiz
            try:
                member = await bot.get_chat_member(ch, user_id)
                if member.status in ["left", "kicked"]:
                    not_joined.append(ch)
            except:
                not_joined.append(ch)
        # https kanallarni tekshirmaymiz
    return not_joined

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "NoName"
    await add_user(user_id, username)

    if user_id == ADMIN_ID:
        await update.message.reply_text("🔥 ADMIN PANEL", reply_markup=admin_keyboard())
        return

    missing = await not_subscribed(user_id, context.bot)
    if missing:
        buttons = []
        for ch in await get_all_channels():
            if ch.startswith("@") or ch.startswith("https://"):
                url = f"https://t.me/{ch[1:]}" if ch.startswith("@") else ch
                buttons.append([InlineKeyboardButton("📢 Kanalga kirish", url=url)])
        buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")])
        await update.message.reply_text("📢 Kanallarga obuna bo‘ling:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    await update.message.reply_text("🎬 Kino kodini yuboring:")

# ========= BUTTON =========
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    missing = await not_subscribed(query.from_user.id, context.bot)
    if missing:
        await query.answer("❌ Hali obuna bo‘lmagansiz!", show_alert=True)
        return
    await query.message.edit_text("✅ Endi kino kodini yuboring!")

# ========= VIDEO =========
async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.user_data.get("step") == "video":
        context.user_data["file"] = update.message.video.file_id
        context.user_data["step"] = "name"
        await update.message.reply_text("🎬 Kino nomini yozing:")

# ========= MESSAGES =========
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    # ====== ADMIN ======
    if user_id == ADMIN_ID:
        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "code"
            await update.message.reply_text("Kino kodini yuboring:")
            return
        if step == "code":
            context.user_data["code"] = text
            context.user_data["step"] = "video"
            await update.message.reply_text("Endi videoni yuboring:")
            return
        if step == "name":
            await add_movie(context.user_data["code"], context.user_data["file"], text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kino saqlandi!", reply_markup=admin_keyboard())
            return
        if text == "🗑 Kino o‘chirish":
            context.user_data["step"] = "del_movie"
            await update.message.reply_text("O‘chirish uchun kod yuboring:")
            return
        if step == "del_movie":
            await del_movie(text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kino o‘chirildi!", reply_markup=admin_keyboard())
            return
        if text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_channel"
            await update.message.reply_text("@username yoki https:// link yuboring:")
            return
        if step == "add_channel":
            await add_channel(text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kanal qo‘shildi!", reply_markup=admin_keyboard())
            return
        if text == "❌ Kanal o‘chirish":
            context.user_data["step"] = "del_channel"
            await update.message.reply_text("@username yoki https:// link yuboring:")
            return
        if step == "del_channel":
            await del_channel(text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kanal o‘chirildi!", reply_markup=admin_keyboard())
            return
        if text == "👥 Userlar":
            users = await get_all_users()
            msg = "👥 Userlar:\n" + "\n".join([f"{u['username']} | {u['user_id']}" for u in users])
            await update.message.reply_text(msg, reply_markup=admin_keyboard())
            return
        if text == "📊 Statistika":
            movies_conn = await asyncpg.connect(DATABASE_URL)
            movies_count = await movies_conn.fetchval("SELECT COUNT(*) FROM movies")
            channels_count = await movies_conn.fetchval("SELECT COUNT(*) FROM channels")
            await movies_conn.close()
            await update.message.reply_text(f"🎬 Kinolar: {movies_count}\n📢 Kanallar: {channels_count}", reply_markup=admin_keyboard())
            return
        if text == "📣 Broadcast":
            context.user_data["step"] = "broadcast_count"
            await update.message.reply_text("📊 Necha foydalanuvchiga xabar yuborishni xohlaysiz?")
            return
        if step == "broadcast_count":
            try:
                count = int(text)
                all_users = await get_all_users()
                if count > len(all_users):
                    count = len(all_users)
                context.user_data["broadcast_count"] = count
                context.user_data["step"] = "broadcast_message"
                await update.message.reply_text(f"✅ Endi xabar matnini yuboring, {count} foydalanuvchiga yuboriladi:")
            except:
                await update.message.reply_text("❌ Iltimos faqat raqam kiriting!")
            return
        if step == "broadcast_message":
            msg_text = text
            all_users = await get_all_users()
            count = context.user_data.get("broadcast_count", len(all_users))
            batch_size = 1000
            success = 0
            for i in range(0, count, batch_size):
                batch = all_users[i:i+batch_size]
                for u in batch:
                    try:
                        await context.bot.send_message(u['user_id'], msg_text)
                        success += 1
                    except:
                        continue
                await asyncio.sleep(1)  # keyingi batch
            context.user_data.clear()
            await update.message.reply_text(f"✅ Xabar {success} foydalanuvchiga yuborildi!", reply_markup=admin_keyboard())
            return

    # ====== FOYDALANUVCHI ======
    missing = await not_subscribed(user_id, context.bot)
    if missing:
        await update.message.reply_text("❌ Avval majburiy kanallarga obuna bo‘ling! /start bosing.")
        return
    movie = await get_movie(text)
    if movie:
        await increase_movie_views(text)
        await update.message.reply_video(movie['file_id'], caption=f"🎬 {movie['name']}")
    else:
        await update.message.reply_text("❌ Kino topilmadi!")

# ========= MAIN =========
async def main():
    await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.VIDEO, video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
    print("🔥 ULTRA ELITE PRO-MAX BOT ISHLADI!")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
