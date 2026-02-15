import sqlite3
import nest_asyncio
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

nest_asyncio.apply()

TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579

# ===== DATABASE =====
conn = sqlite3.connect("database.db", check_same_thread=False)
cur = conn.cursor()

# Bazani sozlash
cur.execute("CREATE TABLE IF NOT EXISTS movies(code TEXT PRIMARY KEY, file_id TEXT, name TEXT, views INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS channels(channel TEXT PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY, username TEXT)")
conn.commit()

# ===== Admin panel keyboard =====
def admin_keyboard():
    keyboard = [
        ["🎬 Kino qo‘shish", "🗑 Kino o‘chirish"],
        ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
        ["👥 Userlar", "📊 Statistika"],
        ["📢 Reklama"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== DB FUNCTIONS =====
def add_movie(code, file_id, name):
    cur.execute("INSERT OR REPLACE INTO movies (code, file_id, name, views) VALUES(?,?,?,0)", (code, file_id, name))
    conn.commit()

def del_movie(code):
    cur.execute("DELETE FROM movies WHERE code=?", (code,))
    conn.commit()

def get_movie(code):
    cur.execute("SELECT file_id, name, views FROM movies WHERE code=?", (code,))
    res = cur.fetchone()
    if res:
        cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (code,))
        conn.commit()
    return res

def add_channel(channel):
    cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (channel,))
    conn.commit()

def del_channel(channel):
    cur.execute("DELETE FROM channels WHERE channel=?", (channel,))
    conn.commit()

def add_user(user_id, username):
    cur.execute("INSERT OR IGNORE INTO users VALUES(?,?)", (str(user_id), str(username)))
    conn.commit()

# ===== CHECK SUB =====
async def not_subscribed(user_id, bot):
    cur.execute("SELECT channel FROM channels")
    channels = [i[0] for i in cur.fetchall()]
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
        cur.execute("SELECT channel FROM channels")
        for ch in cur.fetchall():
            url = f"https://t.me/{ch[0][1:]}" if ch[0].startswith("@") else ch[0]
            buttons.append([InlineKeyboardButton("📢 Kanalga kirish", url=url)])
        buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")])
        await update.message.reply_text("📢 Kanallarga obuna bo‘ling:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    await update.message.reply_text("🎬 Kino kodini yuboring:")

# ===== MEDIA HANDLER =====
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and context.user_data.get("step") == "video":
        file_id = update.message.video.file_id if update.message.video else update.message.document.file_id
        context.user_data["file"] = file_id
        context.user_data["step"] = "name"
        await update.message.reply_text("🎬 Kino nomini yozing:")

# ===== TEXT MESSAGES =====
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if user_id == ADMIN_ID:
        # Admin Buyruqlari
        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "code"
            await update.message.reply_text("Kino kodini yuboring:")
            return
        elif text == "🗑 Kino o‘chirish":
            context.user_data["step"] = "del_movie"
            await update.message.reply_text("O‘chirish uchun kodni yuboring:")
            return
        elif text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_ch"
            await update.message.reply_text("Kanal @username'ini yuboring (Masalan: @kanal_nomi):")
            return
        elif text == "❌ Kanal o‘chirish":
            context.user_data["step"] = "del_ch"
            await update.message.reply_text("O‘chiriladigan kanal @username'ini yuboring:")
            return
        elif text == "📊 Statistika":
            u_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            m_count = cur.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            v_total = cur.execute("SELECT SUM(views) FROM movies").fetchone()[0] or 0
            await update.message.reply_text(f"📊 Statistika:\n\n👥 Azolar: {u_count}\n🎬 Kinolar: {m_count}\n👁 Jami ko'rishlar: {v_total}")
            return
        elif text == "📢 Reklama":
            context.user_data["step"] = "reklama"
            await update.message.reply_text("Reklama xabarini yuboring (Rasm, video yoki matn):")
            return
        elif text == "👥 Userlar":
            cur.execute("SELECT user_id, username FROM users LIMIT 20")
            u_list = "\n".join([f"{i[1]} ({i[0]})" for i in cur.fetchall()])
            await update.message.reply_text(f"Oxirgi 20 ta user:\n\n{u_list}")
            return

        # Qadamlar (Steps)
        if step == "code":
            context.user_data["code"] = text
            context.user_data["step"] = "video"
            await update.message.reply_text("Endi videoni yuboring:")
        elif step == "name":
            add_movie(context.user_data["code"], context.user_data["file"], text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kino saqlandi!", reply_markup=admin_keyboard())
        elif step == "del_movie":
            del_movie(text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kino o‘chirildi!", reply_markup=admin_keyboard())
        elif step == "add_ch":
            add_channel(text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kanal qo‘shildi!", reply_markup=admin_keyboard())
        elif step == "del_ch":
            del_channel(text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kanal o‘chirildi!", reply_markup=admin_keyboard())
        elif step == "reklama":
            cur.execute("SELECT user_id FROM users")
            all_u = cur.fetchall()
            await update.message.reply_text("🚀 Reklama yuborilmoqda...")
            count = 0
            for u in all_u:
                try:
                    await update.message.copy_to(chat_id=u[0])
                    count += 1
                    await asyncio.sleep(0.05)
                except: pass
            await update.message.reply_text(f"✅ {count} kishiga yuborildi.")
            context.user_data.clear()
        return

    # Foydalanuvchi qidiruvi
    movie = get_movie(text)
    if movie:
        await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}\n\n👁 Ko‘rildi: {movie[2]} marta")
    elif not text.startswith("/"):
        await update.message.reply_text("❌ Kino topilmadi!")

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
    print("🔥 BOT TAYYOR!")
    app.run_polling()

if __name__ == "__main__":
    main()
