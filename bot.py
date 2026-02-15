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

# Bazani yaratish va views ustunini tekshirish
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
        # Ko'rilganlar sonini oshirish
        cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (code,))
        conn.commit()
    return res

def add_user(user_id, username):
    cur.execute("INSERT OR IGNORE INTO users VALUES(?,?)", (str(user_id), str(username)))
    conn.commit()

# ===== CHECK SUB =====
async def not_subscribed(user_id, bot):
    channels = cur.execute("SELECT channel FROM channels").fetchall()
    channels = [i[0] for i in channels]
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
        all_ch = cur.fetchall()
        for ch in all_ch:
            url = f"https://t.me/{ch[0][1:]}" if ch[0].startswith("@") else ch[0]
            buttons.append([InlineKeyboardButton("📢 Kanalga kirish", url=url)])
        buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")])
        await update.message.reply_text("📢 Kanallarga obuna bo‘ling:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    await update.message.reply_text("🎬 Kino kodini yuboring:")

# ===== MEDIA HANDLER (Video yoki Document) =====
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    step = context.user_data.get("step")
    if step == "video":
        if update.message.video:
            file_id = update.message.video.file_id
        elif update.message.document:
            file_id = update.message.document.file_id
        else:
            await update.message.reply_text("Iltimos, kino faylini yuboring!")
            return
            
        context.user_data["file"] = file_id
        context.user_data["step"] = "name"
        await update.message.reply_text("🎬 Kino nomini yozing:")

# ===== TEXT MESSAGES =====
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if user_id == ADMIN_ID:
        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "code"
            await update.message.reply_text("Kino kodini yuboring:")
            return
        
        elif step == "code":
            context.user_data["code"] = text
            context.user_data["step"] = "video"
            await update.message.reply_text("Endi kinoni (video yoki fayl) yuboring:")
            return

        elif step == "name":
            add_movie(context.user_data["code"], context.user_data["file"], text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kino muvaffaqiyatli saqlandi!", reply_markup=admin_keyboard())
            return

        elif text == "📊 Statistika":
            u_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            m_count = cur.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            total_views = cur.execute("SELECT SUM(views) FROM movies").fetchone()[0] or 0
            await update.message.reply_text(f"📊 **Bot Statistikasi:**\n\n👥 Azolar: {u_count} ta\n🎬 Kinolar: {m_count} ta\n👁 Ko'rishlar: {total_views} ta")
            return

        elif text == "📢 Reklama":
            context.user_data["step"] = "reklama"
            await update.message.reply_text("Reklama xabarini yuboring (xohlagan turda):")
            return

        elif step == "reklama":
            cur.execute("SELECT user_id FROM users")
            all_users = cur.fetchall()
            count = 0
            msg = await update.message.reply_text("🚀 Yuborilmoqda...")
            for u in all_users:
                try:
                    await update.message.copy_to(chat_id=u[0])
                    count += 1
                    if count % 50 == 0: await msg.edit_text(f"🚀 Yuborilmoqda: {count}")
                except: pass
            await update.message.reply_text(f"✅ Reklama {count} kishiga yuborildi.")
            context.user_data.clear()
            return
            
        # Kanal va o'chirish amallari
        if text == "🗑 Kino o‘chirish":
            context.user_data["step"] = "del_movie"
            await update.message.reply_text("O‘chirish uchun kodni yuboring:")
            return
        elif step == "del_movie":
            del_movie(text)
            await update.message.reply_text("🗑 Kino o‘chirildi.")
            context.user_data.clear()
            return

    # Foydalanuvchi qismi
    movie = get_movie(text)
    if movie:
        await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}\n\n👁 Ko‘rildi: {movie[2]} marta")
    else:
        if not text.startswith("/"):
            await update.message.reply_text("❌ Bunday kodli kino topilmadi.")

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
    print("🔥 BOT ISHLADI!")
    app.run_polling()

if __name__ == "__main__":
    main()
