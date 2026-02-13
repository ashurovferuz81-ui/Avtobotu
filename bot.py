import sqlite3
import nest_asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

nest_asyncio.apply()

TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579

# ===== DATABASE =====
conn = sqlite3.connect("database.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS movies(
    code TEXT PRIMARY KEY,
    file_id TEXT,
    name TEXT,
    views INTEGER DEFAULT 0
)
""")

cur.execute("CREATE TABLE IF NOT EXISTS channels(channel TEXT PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY, username TEXT)")
conn.commit()


# ===== Admin panel keyboard =====
def admin_keyboard():
    keyboard = [
        ["🎬 Kino qo‘shish", "🗑 Kino o‘chirish"],
        ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
        ["👥 Userlar", "📊 Statistika"],
        ["🎥 Kinolar ro‘yxati"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ===== DB FUNCTIONS =====
def add_movie(code, file_id, name):
    cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?,0)", (code, file_id, name))
    conn.commit()

def del_movie(code):
    cur.execute("DELETE FROM movies WHERE code=?", (code,))
    conn.commit()

def get_movie(code):
    cur.execute("SELECT file_id,name FROM movies WHERE code=?", (code,))
    return cur.fetchone()

def increment_view(code):
    cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (code,))
    conn.commit()

def get_movies_stats():
    cur.execute("SELECT name,code,views FROM movies ORDER BY views DESC")
    return cur.fetchall()

def add_channel(channel):
    cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (channel,))
    conn.commit()

def del_channel(channel):
    cur.execute("DELETE FROM channels WHERE channel=?", (channel,))
    conn.commit()

def get_all_channels():
    cur.execute("SELECT channel FROM channels")
    return [i[0] for i in cur.fetchall()]

def add_user(user_id, username):
    cur.execute("INSERT OR IGNORE INTO users VALUES(?,?)", (user_id, username))
    conn.commit()

def get_users_count():
    cur.execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]

def get_channels_count():
    cur.execute("SELECT COUNT(*) FROM channels")
    return cur.fetchone()[0]


# ===== CHECK SUB =====
async def not_subscribed(user_id, bot):
    channels = get_all_channels()
    not_joined = []

    for ch in channels:
        if ch.startswith("@"):
            try:
                member = await bot.get_chat_member(ch, user_id)
                if member.status in ["left", "kicked"]:
                    not_joined.append(ch)
            except:
                not_joined.append(ch)

    return not_joined


# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "NoName"

    add_user(user_id, username)

    if user_id == ADMIN_ID:
        await update.message.reply_text("🔥 ADMIN PANEL", reply_markup=admin_keyboard())
        return

    missing = await not_subscribed(user_id, context.bot)

    if missing:
        buttons = []
        for ch in get_all_channels():
            url = f"https://t.me/{ch[1:]}" if ch.startswith("@") else ch
            buttons.append([InlineKeyboardButton("📢 Kanalga kirish", url=url)])

        buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")])

        await update.message.reply_text(
            "📢 Kanallarga obuna bo‘ling:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    await update.message.reply_text("🎬 Kino kodini yuboring:")


# ===== BUTTON =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    missing = await not_subscribed(query.from_user.id, context.bot)

    if missing:
        await query.answer("❌ Hali obuna bo‘lmagansiz!", show_alert=True)
        return

    await query.message.edit_text("✅ Endi kino kodini yuboring!")


# ===== VIDEO =====
async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("step") == "video":
        context.user_data["file"] = update.message.video.file_id
        context.user_data["step"] = "name"
        await update.message.reply_text("🎬 Kino nomini yozing:")


# ===== TEXT =====
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    # ===== ADMIN =====
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
            add_movie(context.user_data["code"], context.user_data["file"], text)
            context.user_data.clear()

            await update.message.reply_text("✅ Kino saqlandi!", reply_markup=admin_keyboard())
            return

        if text == "🗑 Kino o‘chirish":
            context.user_data["step"] = "del_movie"
            await update.message.reply_text("Kod yuboring:")
            return

        if step == "del_movie":
            del_movie(text)
            context.user_data.clear()
            await update.message.reply_text("✅ O‘chirildi!", reply_markup=admin_keyboard())
            return

        if text == "📊 Statistika":

            users = get_users_count()
            channels = get_channels_count()
            movies = len(get_movies_stats())

            msg = f"""
🔥 BOT STATISTIKASI

👥 Foydalanuvchilar: {users}
📢 Kanallar: {channels}
🎬 Kinolar: {movies}
"""

            await update.message.reply_text(msg, reply_markup=admin_keyboard())
            return

        if text == "🎥 Kinolar ro‘yxati":

            movies = get_movies_stats()

            if not movies:
                await update.message.reply_text("Kino yo‘q.")
                return

            msg = "🎬 KINOLAR STATISTIKASI:\n\n"

            for name, code, views in movies:
                msg += f"""
🎥 {name}
🔑 Kod: {code}
👁 Ko‘rilgan: {views}

"""

            await update.message.reply_text(msg)
            return


    # ===== USER =====

    missing = await not_subscribed(user_id, context.bot)

    if missing:
        await update.message.reply_text("❌ Avval obuna bo‘ling! /start bosing.")
        return

    movie = get_movie(text)

    if movie:

        increment_view(text)  # <<< ENG MUHIM QO‘SHIMCHA

        await update.message.reply_video(
            movie[0],
            caption=f"🎬 {movie[1]}"
        )

    else:
        await update.message.reply_text("❌ Kino topilmadi!")


# ===== MAIN =====
def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.VIDEO, video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

    print("🔥 ULTRA PRO BOT ISHLADI!")
    app.run_polling()


if __name__ == "__main__":
    main()
