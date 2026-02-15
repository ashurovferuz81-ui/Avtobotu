import sqlite3
import nest_asyncio
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

nest_asyncio.apply()

TOKEN = "TOKENINGNI_BU_YERGA_QO'Y"
ADMIN_ID = 5775388579

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS movies(code TEXT PRIMARY KEY, file_id TEXT, name TEXT, views INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS channels(channel TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY, username TEXT)")
    conn.commit()
    return conn

conn = init_db()
cur = conn.cursor()

# ================= KEYBOARD =================
def admin_keyboard():
    keyboard = [
        ["🎬 Kino qo‘shish", "🗑 Kino o‘chirish"],
        ["📢 Kanal qo‘shish", "📊 Statistika"],
        ["📢 Reklama"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "NoName"

    cur.execute("INSERT OR REPLACE INTO users VALUES(?,?)", (user_id, username))
    conn.commit()

    if int(user_id) == ADMIN_ID:
        await update.message.reply_text("🔥 ADMIN PANEL", reply_markup=admin_keyboard())
        return

    cur.execute("SELECT channel FROM channels")
    channels = [i[0] for i in cur.fetchall()]
    not_joined = []

    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                not_joined.append(ch)
        except:
            not_joined.append(ch)

    if not_joined:
        buttons = [[InlineKeyboardButton("📢 A'zo bo'lish", url=f"https://t.me/{c[1:]}")] for c in not_joined]
        buttons.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub")])
        await update.message.reply_text("Botdan foydalanish uchun kanalga a'zo bo'ling!",
                                        reply_markup=InlineKeyboardMarkup(buttons))
        return

    await update.message.reply_text("🎬 Kino kodini yuboring:")

# ================= REKLAMA =================
async def send_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = context.user_data.get("limit")

    if not limit or limit <= 0:
        cur.execute("SELECT user_id FROM users")
    else:
        cur.execute(f"SELECT user_id FROM users LIMIT {int(limit)}")

    users = cur.fetchall()

    if not users:
        await update.message.reply_text("❌ User topilmadi!")
        return

    success = 0
    fail = 0
    status = await update.message.reply_text("🚀 Reklama yuborilmoqda...")

    for user in users:
        user_id = int(user[0])
        try:
            if update.message.text:
                await context.bot.send_message(user_id, update.message.text)
            elif update.message.photo:
                await context.bot.send_photo(user_id, update.message.photo[-1].file_id,
                                             caption=update.message.caption)
            elif update.message.video:
                await context.bot.send_video(user_id, update.message.video.file_id,
                                             caption=update.message.caption)
            success += 1
            await asyncio.sleep(0.05)

        except:
            cur.execute("DELETE FROM users WHERE user_id=?", (user_id,))
            conn.commit()
            fail += 1

    await status.edit_text(f"🏁 Tugadi\n\n✅ Yetkazildi: {success}\n❌ O‘chirilgan: {fail}")
    context.user_data.clear()

# ================= MESSAGE =================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    # ===== ADMIN =====
    if user_id == ADMIN_ID:

        if text == "📊 Statistika":
            cur.execute("SELECT COUNT(*) FROM users")
            users = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM movies")
            movies = cur.fetchone()[0]
            await update.message.reply_text(f"👥 Userlar: {users}\n🎬 Kinolar: {movies}")
            return

        if text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_channel"
            await update.message.reply_text("Kanal @username yuboring:")
            return

        if step == "add_channel":
            cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (text,))
            conn.commit()
            await update.message.reply_text("✅ Qo‘shildi")
            context.user_data.clear()
            return

        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "wait_video"
            await update.message.reply_text("Video yuboring:")
            return

        if step == "wait_video" and update.message.video:
            context.user_data["file_id"] = update.message.video.file_id
            context.user_data["step"] = "wait_code"
            await update.message.reply_text("Kino kodini yuboring:")
            return

        if step == "wait_code":
            context.user_data["code"] = text
            context.user_data["step"] = "wait_name"
            await update.message.reply_text("Kino nomini yuboring:")
            return

        if step == "wait_name":
            file_id = context.user_data["file_id"]
            code = context.user_data["code"]
            name = text
            cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?,0)", (code, file_id, name))
            conn.commit()
            await update.message.reply_text("✅ Kino qo‘shildi")
            context.user_data.clear()
            return

        if text == "📢 Reklama":
            cur.execute("SELECT COUNT(*) FROM users")
            total = cur.fetchone()[0]
            context.user_data["step"] = "wait_limit"
            await update.message.reply_text(f"Jami user: {total}\nNechta odamga yuboramiz? (0 = hammasi)")
            return

        if step == "wait_limit":
            if text.isdigit():
                context.user_data["limit"] = int(text)
                context.user_data["step"] = "wait_ads"
                await update.message.reply_text("Reklama xabarini yuboring:")
            else:
                await update.message.reply_text("Faqat son yozing")
            return

        if step == "wait_ads":
            await send_ads(update, context)
            return

    # ===== USER KINO QIDIRISH =====
    cur.execute("SELECT file_id, name, views FROM movies WHERE code=?", (text,))
    movie = cur.fetchone()

    if movie:
        cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (text,))
        conn.commit()
        await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}\n👁 {movie[2]+1}")
    elif not text.startswith("/"):
        await update.message.reply_text("❌ Kino topilmadi")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.TEXT | filters.VIDEO | filters.PHOTO, messages))

    print("Bot ishga tushdi 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
