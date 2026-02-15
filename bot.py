import sqlite3
import nest_asyncio
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

nest_asyncio.apply()

# YANGI TOKEN
TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579

# ===== DATABASE =====
conn = sqlite3.connect("database.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS movies(code TEXT PRIMARY KEY, file_id TEXT, name TEXT, views INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS channels(channel TEXT PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY, username TEXT)")
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

# ===== DB FUNCTIONS =====
def add_movie(code, file_id, name):
    cur.execute("INSERT OR REPLACE INTO movies (code, file_id, name, views) VALUES(?,?,?,0)", (code, file_id, name))
    conn.commit()

def get_movie(code):
    cur.execute("SELECT file_id, name, views FROM movies WHERE code=?", (code,))
    res = cur.fetchone()
    if res:
        cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (code,))
        conn.commit()
    return res

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
                if member.status in ["left", "kicked", "left"]:
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

# ===== CALLBACK (CHECK SUB) =====
async def check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    missing = await not_subscribed(user_id, context.bot)
    
    if missing:
        await query.answer("❌ Hali hamma kanallarga obuna bo'lmagansiz!", show_alert=True)
    else:
        await query.message.delete()
        await context.bot.send_message(user_id, "✅ Rahmat! Endi kino kodini yuborishingiz mumkin:")

# ===== ADMIN LOGIC =====
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if user_id == ADMIN_ID:
        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "code"
            await update.message.reply_text("Kino kodini yuboring:")
            return
        
        elif text == "📢 Reklama":
            cur.execute("SELECT COUNT(*) FROM users")
            u_count = cur.fetchone()[0]
            context.user_data["step"] = "rek_soni"
            await update.message.reply_text(f"Botda jami {u_count} ta user bor.\nNecha kishiga yubormoqchisiz? (Son kiriting):")
            return

        elif step == "rek_soni":
            if not text.isdigit():
                await update.message.reply_text("Iltimos faqat son yozing!")
                return
            
            requested_count = int(text)
            cur.execute("SELECT COUNT(*) FROM users")
            actual_count = cur.fetchone()[0]

            if requested_count > actual_count:
                await update.message.reply_text(f"❌ Botda buncha foydalanuvchi yo'q! Jami: {actual_count}")
                context.user_data.clear()
                return
            
            context.user_data["rek_limit"] = requested_count
            context.user_data["step"] = "rek_xabar"
            await update.message.reply_text(f"Yaxshi, {requested_count} kishi uchun reklama xabarini yuboring:")
            return

        elif step == "rek_xabar":
            limit = context.user_data.get("rek_limit")
            cur.execute("SELECT user_id FROM users LIMIT ?", (limit,))
            all_u = cur.fetchall()
            
            await update.message.reply_text("🚀 Reklama yuborish boshlandi...")
            count = 0
            for u in all_u:
                try:
                    await update.message.copy_to(chat_id=u[0])
                    count += 1
                    await asyncio.sleep(0.05)
                except: pass
            
            await update.message.reply_text(f"✅ Reklama {count} kishiga muvaffaqiyatli yuborildi!", reply_markup=admin_keyboard())
            context.user_data.clear()
            return

        # Qolgan admin amallari...
        if step == "code":
            context.user_data["code"] = text
            context.user_data["step"] = "video"
            await update.message.reply_text("Endi videoni yuboring:")
            return
        elif step == "name":
            add_movie(context.user_data["code"], context.user_data["file"], text)
            context.user_data.clear()
            await update.message.reply_text("✅ Kino saqlandi!", reply_markup=admin_keyboard())
            return
        elif text == "📊 Statistika":
            u_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            m_count = cur.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            v_total = cur.execute("SELECT SUM(views) FROM movies").fetchone()[0] or 0
            await update.message.reply_text(f"📊 Statistika:\n\n👥 Azolar: {u_count}\n🎬 Kinolar: {m_count}\n👁 Ko'rishlar: {v_total}")
            return
        elif text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_ch"
            await update.message.reply_text("Kanal @username'ini yuboring:")
            return
        elif step == "add_ch":
            cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (text,))
            conn.commit()
            await update.message.reply_text("✅ Kanal qo‘shildi!")
            context.user_data.clear()
            return
        elif text == "❌ Kanal o‘chirish":
            context.user_data["step"] = "del_ch"
            await update.message.reply_text("O‘chiriladigan kanal @username'ini yuboring:")
            return
        elif step == "del_ch":
            cur.execute("DELETE FROM channels WHERE channel=?", (text,))
            conn.commit()
            await update.message.reply_text("❌ Kanal o‘chirildi!")
            context.user_data.clear()
            return

    # Foydalanuvchi qidiruvi
    movie = get_movie(text)
    if movie:
        await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}\n\n👁 Ko‘rildi: {movie[2]} marta")
    elif not text.startswith("/"):
        await update.message.reply_text("❌ Kino topilmadi!")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and context.user_data.get("step") == "video":
        file_id = update.message.video.file_id if update.message.video else update.message.document.file_id
        context.user_data["file"] = file_id
        context.user_data["step"] = "name"
        await update.message.reply_text("🎬 Kino nomini yozing:")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_callback, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
    print("🔥 BOT ISHLAYAPTI...")
    app.run_polling()

if __name__ == "__main__":
    main()
