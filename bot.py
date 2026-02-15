import sqlite3
import nest_asyncio
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

nest_asyncio.apply()

# TOKEN VA ADMIN
TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579

# ===== DATABASE =====
def get_db():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    return conn

conn = get_db()
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS movies(code TEXT PRIMARY KEY, file_id TEXT, name TEXT, views INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS channels(channel TEXT PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT)")
conn.commit()

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
    user_id = update.effective_user.id
    username = update.effective_user.username or "NoName"
    
    # Userni bazaga qo'shish (Majburiy)
    cur.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES(?,?)", (user_id, str(username)))
    conn.commit()

    if user_id == ADMIN_ID:
        await update.message.reply_text("🔥 ADMIN PANEL", reply_markup=admin_keyboard())
        return

    # Kanalga tekshirish
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
        buttons = []
        for ch in not_joined:
            url = f"https://t.me/{ch[1:]}"
            buttons.append([InlineKeyboardButton(f"📢 Obuna bo'lish", url=url)])
        buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")])
        await update.message.reply_text("📢 Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    await update.message.reply_text("🎬 Kino kodini yuboring:")

# ===== CALLBACK =====
async def check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.delete()
    # Qayta start berish
    await start(update, context)

# ===== ADMIN MESSAGES =====
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if user_id == ADMIN_ID:
        # TUGMALAR
        if text == "📢 Reklama":
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            context.user_data["step"] = "get_limit"
            await update.message.reply_text(f"📢 Jami userlar: {count} ta\nNecha kishiga reklama yubormoqchisiz?")
            return

        elif text == "📊 Statistika":
            cur.execute("SELECT COUNT(*) FROM users")
            u = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM movies")
            m = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM channels")
            c = cur.fetchone()[0]
            cur.execute("SELECT SUM(views) FROM movies")
            v = cur.fetchone()[0] or 0
            await update.message.reply_text(f"📊 Statistika:\n\n👥 Userlar: {u}\n🎬 Kinolar: {m}\n📢 Kanallar: {c}\n👁 Ko'rilgan: {v}")
            return

        # REKLAMA LOGIKASI
        if step == "get_limit":
            if text.isdigit():
                context.user_data["limit"] = int(text)
                context.user_data["step"] = "get_ads"
                await update.message.reply_text("Endi reklama xabarini yuboring (xohlagan turda):")
            else:
                await update.message.reply_text("Faqat son kiriting!")
            return

        elif step == "get_ads":
            limit = context.user_data.get("limit")
            cur.execute("SELECT user_id FROM users LIMIT ?", (limit,))
            users = cur.fetchall()
            
            success = 0
            error = 0
            msg = await update.message.reply_text("🚀 Reklama yuborish boshlandi...")
            
            for row in users:
                target_id = row[0]
                try:
                    # copy_to - bu eng ishonchli usul, u hamma narsani original holda yuboradi
                    await update.message.copy_to(chat_id=target_id)
                    success += 1
                    await asyncio.sleep(0.05) # Bloklanmaslik uchun
                except:
                    error += 1
            
            await msg.edit_text(f"🏁 Reklama yakunlandi!\n✅ Yetkazildi: {success}\n❌ Bloklagan: {error}")
            context.user_data.clear()
            return

        # KINO QO'SHISH
        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "k_code"
            await update.message.reply_text("Kino kodini yozing:")
            return
        elif step == "k_code":
            context.user_data["c"] = text
            context.user_data["step"] = "k_file"
            await update.message.reply_text("Kinoni yuboring (Video):")
            return
        elif step == "k_name":
            cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?,0)", (context.user_data["c"], context.user_data["f"], text))
            conn.commit()
            await update.message.reply_text("✅ Kino saqlandi!")
            context.user_data.clear()
            return

        # KANAL QO'SHISH/OCHIRISH
        if text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_ch"
            await update.message.reply_text("Kanal @username'ini yozing:")
            return
        elif step == "add_ch":
            cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (text,))
            conn.commit()
            await update.message.reply_text("✅ Kanal qo'shildi!")
            context.user_data.clear()
            return
        if text == "❌ Kanal o‘chirish":
            context.user_data["step"] = "del_ch"
            await update.message.reply_text("Kanal @username'ini yozing:")
            return
        elif step == "del_ch":
            cur.execute("DELETE FROM channels WHERE channel=?", (text,))
            conn.commit()
            await update.message.reply_text("❌ Kanal o'chirildi!")
            context.user_data.clear()
            return

    # USER KINO QIDIRISH
    cur.execute("SELECT file_id, name, views FROM movies WHERE code=?", (text,))
    res = cur.fetchone()
    if res:
        cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (text,))
        conn.commit()
        await update.message.reply_video(res[0], caption=f"🎬 {res[1]}\n\n👁 Ko'rildi: {res[2]+1}")
    elif not text.startswith("/"):
        await update.message.reply_text("❌ Kino topilmadi!")

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and context.user_data.get("step") == "k_file":
        context.user_data["f"] = update.message.video.file_id
        context.user_data["step"] = "k_name"
        await update.message.reply_text("🎬 Kino nomini yozing:")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_callback, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
    print("🚀 BOT ONLINE!")
    app.run_polling()

if __name__ == "__main__":
    main()
