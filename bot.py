import os
import sqlite3
import nest_asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from utils import top_movies, random_movies

nest_asyncio.apply()
load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ===== DATABASE =====
DB_PATH = "database.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

# --- Tables ---
cur.execute("CREATE TABLE IF NOT EXISTS movies(code TEXT PRIMARY KEY, file_id TEXT, name TEXT, views INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS channels(channel TEXT PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY, username TEXT)")
conn.commit()

# ===== ADMIN KEYBOARD =====
def admin_keyboard():
    keyboard = [
        ["🎬 Kino qo‘shish", "🗑 Kino o‘chirish"],
        ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
        ["👥 Userlar", "📊 Statistika"],
        ["📡 Broadcast", "🏆 Reytingli kinolar"]
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
    cur.execute("SELECT file_id,name,views FROM movies WHERE code=?", (code,))
    return cur.fetchone()

def update_movie_views(code):
    cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (code,))
    conn.commit()

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

def get_all_users():
    cur.execute("SELECT user_id, username FROM users")
    return cur.fetchall()

def get_all_movies():
    cur.execute("SELECT code,name,views FROM movies")
    return cur.fetchall()

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "NoName"
    add_user(user_id, username)

    if user_id == ADMIN_ID:
        await update.message.reply_text("🔥 ADMIN PANEL", reply_markup=admin_keyboard())
        return

    await update.message.reply_text("🎬 Kino kodini yuboring:")

# ===== ADMIN STAT =====
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    users = get_all_users()
    channels = get_all_channels()
    movies = get_all_movies()

    msg = f"📊 Statistika:\n\nKinolar:\n"
    for m in movies:
        msg += f"{m[0]} | {m[1]} | Ko‘rganlar: {m[2]}\n"
    msg += "\nKanallar:\n"
    for c in channels:
        msg += f"{c}\n"
    msg += f"\nUserlar: {len(users)}"
    await update.message.reply_text(msg, reply_markup=admin_keyboard())

# ===== VIDEO HANDLER =====
async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    if context.user_data.get("step") == "video":
        context.user_data["file"] = update.message.video.file_id
        context.user_data["step"] = "name"
        await update.message.reply_text("🎬 Kino nomini yozing:")

# ===== TEXT HANDLER =====
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    # --- ADMIN LOGIC ---
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
            await update.message.reply_text("O‘chirish uchun kod yuboring:")
            return
        if step == "del_movie":
            del_movie(text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kino o‘chirildi!", reply_markup=admin_keyboard())
            return
        if text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_channel"
            await update.message.reply_text("@username yoki https:// link yuboring:")
            return
        if step == "add_channel":
            add_channel(text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kanal qo‘shildi!", reply_markup=admin_keyboard())
            return
        if text == "❌ Kanal o‘chirish":
            context.user_data["step"] = "del_channel"
            await update.message.reply_text("@username yoki https:// link yuboring:")
            return
        if step == "del_channel":
            del_channel(text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kanal o‘chirildi!", reply_markup=admin_keyboard())
            return
        if text == "👥 Userlar":
            users = get_all_users()
            msg = "👥 Userlar:\n" + "\n".join([f"{u[1]} | {u[0]}" for u in users])
            await update.message.reply_text(msg, reply_markup=admin_keyboard())
            return
        if text == "📊 Statistika":
            await admin_stats(update, context)
            return

    # --- FOYDALANUVCHI LOGIC ---
    movie = get_movie(text)
    if movie:
        update_movie_views(text)
        await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}")
    else:
        await update.message.reply_text("❌ Kino topilmadi!")

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

    print("🔥 ULTRA ELITE BOT ISHLADI!")
    app.run_polling()

if __name__ == "__main__":
    main()
