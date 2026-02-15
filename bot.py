import sqlite3
import nest_asyncio
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

nest_asyncio.apply()

# TOKEN VA ADMIN
TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579

# ===== DATABASE SOZLAMALARI =====
def init_db():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS movies(code TEXT PRIMARY KEY, file_id TEXT, name TEXT, views INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS channels(channel TEXT PRIMARY KEY)")
    # user_id ni matn (TEXT) sifatida saqlash xatolikni kamaytiradi
    cur.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY, username TEXT)")
    conn.commit()
    return conn

conn = init_db()
cur = conn.cursor()

# ===== KEYBOARDS =====
def admin_keyboard():
    keyboard = [
        ["🎬 Kino qo‘shish", "🗑 Kino o‘chirish"],
        ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
        ["👥 Userlar", "📊 Statistika"],
        ["📢 Reklama"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "NoName"
    
    # FOYDALANUVCHINI BAZAGA QO'SHISH (Eng muhim joyi)
    cur.execute("INSERT OR REPLACE INTO users (user_id, username) VALUES(?,?)", (user_id, username))
    conn.commit()

    if int(user_id) == ADMIN_ID:
        await update.message.reply_text("🔥 ADMIN PANELGA XUSH KELIBSIZ", reply_markup=admin_keyboard())
        return

    # Kanallarni tekshirish
    cur.execute("SELECT channel FROM channels")
    channels = [i[0] for i in cur.fetchall()]
    not_joined = []
    for ch in channels:
        if ch.startswith("@"):
            try:
                member = await context.bot.get_chat_member(ch, user_id)
                if member.status in ["left", "kicked"]:
                    not_joined.append(ch)
            except:
                not_joined.append(ch)
    
    if not_joined:
        buttons = [[InlineKeyboardButton("📢 Kanalga a'zo bo'lish", url=f"https://t.me/{c[1:]}")] for c in not_joined]
        buttons.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub")])
        await update.message.reply_text("Obuna bo'lmagansiz!", reply_markup=InlineKeyboardMarkup(buttons))
        return

    await update.message.reply_text("🎬 Kino kodini yuboring:")

# ===== REKLAMA YUBORISH (YANGI USUL) =====
async def send_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = context.user_data.get("limit")
    cur.execute("SELECT user_id FROM users LIMIT ?", (limit,))
    rows = cur.fetchall()
    
    success = 0
    fail = 0
    status_msg = await update.message.reply_text("🚀 Reklama yuborilmoqda...")

    for row in rows:
        target_id = row[0]
        try:
            # copy_to ishlamasa send_message'ga o'tadi
            await update.message.copy_to(chat_id=target_id)
            success += 1
            await asyncio.sleep(0.1) # Telegram spamdan himoya
        except Exception as e:
            print(f"Xato {target_id}: {e}")
            fail += 1
    
    await status_msg.edit_text(f"🏁 Yakunlandi!\n✅ Yetkazildi: {success}\n❌ Yetkazilmadi: {fail}")
    context.user_data.clear()

# ===== MESSAGES =====
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if user_id == ADMIN_ID:
        if text == "📢 Reklama":
            cur.execute("SELECT COUNT(*) FROM users")
            total = cur.fetchone()[0]
            context.user_data["step"] = "wait_limit"
            await update.message.reply_text(f"Jami foydalanuvchilar: {total} ta.\nNecha kishiga yuboramiz?")
            return

        elif step == "wait_limit":
            if text.isdigit():
                context.user_data["limit"] = int(text)
                context.user_data["step"] = "wait_ads"
                await update.message.reply_text("Endi reklama xabarini yuboring (rasm, video yoki matn):")
            else:
                await update.message.reply_text("Faqat son yozing!")
            return

        elif step == "wait_ads":
            await send_ads(update, context)
            return

        # Statistika
        if text == "📊 Statistika":
            cur.execute("SELECT COUNT(*) FROM users")
            u = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM movies")
            m = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM channels")
            c = cur.fetchone()[0]
            await update.message.reply_text(f"📊 Statistika:\n👤 Userlar: {u}\n🎬 Kinolar: {m}\n📢 Kanallar: {c}")
            return

        # Kanal qo'shish
        if text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_ch"
            await update.message.reply_text("Kanal @username'ini yuboring:")
            return
        elif step == "add_ch":
            cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (text,))
            conn.commit()
            await update.message.reply_text("✅ Kanal qo'shildi!")
            context.user_data.clear()
            return

    # User qidiruvi
    cur.execute("SELECT file_id, name, views FROM movies WHERE code=?", (text,))
    res = cur.fetchone()
    if res:
        cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (text,))
        conn.commit()
        await update.message.reply_video(res[0], caption=f"🎬 {res[1]}\n👁 {res[2]+1}")
    elif not text.startswith("/"):
        await update.message.reply_text("Kino topilmadi!")

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admin kino qo'shish jarayoni (file_id ni olish)
    pass # Kerakli joyga yuqoridagi logic'ni qo'shish mumkin

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, messages)) 
    print("Bot yoqildi!")
    app.run_polling()

if __name__ == "__main__":
    main()
