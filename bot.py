import sqlite3
import nest_asyncio
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

nest_asyncio.apply()

TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
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
        ["🎬 Ommaviy qo‘shish", "🗑 Kino o‘chirish"],
        ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
        ["👥 Userlar", "📊 Statistika"],
        ["📢 Reklama"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= START (Tuzatilgan) =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or "NoName"

    cur.execute("INSERT OR REPLACE INTO users VALUES(?,?)", (user_id, username))
    conn.commit()

    if int(user_id) == ADMIN_ID:
        msg = update.message or update.callback_query.message
        await msg.reply_text("🔥 ADMIN PANEL", reply_markup=admin_keyboard())
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
        buttons = [[InlineKeyboardButton("📢 A'zo bo'lish", url=f"https://t.me/{c[1:]}" if c.startswith("@") else c)] for c in not_joined]
        buttons.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub")])
        
        if update.callback_query:
            await update.callback_query.answer("❌ Hali a'zo emassiz!", show_alert=True)
        else:
            await update.message.reply_text("Botdan foydalanish uchun kanallarga a'zo bo'ling!", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if update.callback_query:
        await update.callback_query.message.delete()
        await context.bot.send_message(user_id, "✅ Rahmat! Endi kino kodini yuboring:")
    else:
        await update.message.reply_text("🎬 Kino kodini yuboring:")

# ================= REKLAMA (TEGILMADI) =================
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
    success, fail = 0, 0
    status = await update.message.reply_text("🚀 Reklama yuborilmoqda...")
    for user in users:
        u_id = user[0]
        try:
            if update.message.text: await context.bot.send_message(u_id, update.message.text)
            elif update.message.photo: await context.bot.send_photo(u_id, update.message.photo[-1].file_id, caption=update.message.caption)
            elif update.message.video: await context.bot.send_video(u_id, update.message.video.file_id, caption=update.message.caption)
            success += 1
            await asyncio.sleep(0.05)
        except:
            cur.execute("DELETE FROM users WHERE user_id=?", (u_id,))
            conn.commit()
            fail += 1
    await status.edit_text(f"🏁 Tugadi\n✅ Yetkazildi: {success}\n❌ O‘chirilgan: {fail}")
    context.user_data.clear()

# ================= MESSAGE HANDLER =================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if user_id == ADMIN_ID:
        # 1. OMMAVIY QO'SHISH BOSHLANISHI
        if text == "🎬 Ommaviy qo‘shish":
            context.user_data["step"] = "wait_batch_codes"
            await update.message.reply_text("Kino kodlarini yuboring (Masalan: 1, 2, 3 yoki 101 102 103):")
            return

        # 2. KODLARNI QABUL QILISH
        if step == "wait_batch_codes":
            import re
            codes = re.findall(r'\d+', text) # Faqat sonlarni ajratib oladi
            if not codes:
                await update.message.reply_text("Xato! Hech bo'lmasa bitta son yuboring.")
                return
            context.user_data["batch_codes"] = codes
            context.user_data["step"] = "wait_batch_videos"
            await update.message.reply_text(f"✅ {len(codes)} ta kod qabul qilindi: {', '.join(codes)}\n\nEndi videolarni ketma-ket yuboring. Men ularni tartib bilan saqlayman.")
            return

        # 3. VIDEOLARNI QABUL QILISH (Media handler orqali ham ishlaydi)
        if step == "wait_batch_videos" and update.message.video:
            codes = context.user_data.get("batch_codes", [])
            if codes:
                current_code = codes.pop(0) # Birinchi kodni oladi
                file_id = update.message.video.file_id
                # Ism berish (ixtiyoriy, hozircha 'Kino {kod}' deb saqlaydi)
                cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?,0)", (current_code, file_id, f"Kino {current_code}"))
                conn.commit()
                
                if codes:
                    context.user_data["batch_codes"] = codes
                    await update.message.reply_text(f"✅ Kod {current_code} saqlandi. Yana {len(codes)} ta video kutilyapti...")
                else:
                    await update.message.reply_text("🎉 Hammasi tugadi! Barcha kinolar saqlandi.", reply_markup=admin_keyboard())
                    context.user_data.clear()
            return

        # STATISTIKA VA BOSHQA TUGMALAR
        if text == "📊 Statistika":
            cur.execute("SELECT COUNT(*) FROM users"); u = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM movies"); m = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM channels"); c = cur.fetchone()[0]
            await update.message.reply_text(f"📊 Statistika\n\n👤 Userlar: {u}\n🎬 Kinolar: {m}\n📢 Kanallar: {c}")
            return

        if text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_channel"
            await update.message.reply_text("Kanal @username yuboring:")
            return
        
        if step == "add_channel":
            cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (text,))
            conn.commit()
            await update.message.reply_text("✅ Qo‘shildi"); context.user_data.clear()
            return

        if text == "❌ Kanal o‘chirish":
            context.user_data["step"] = "del_channel"
            await update.message.reply_text("Kanal @username yuboring:")
            return
        
        if step == "del_channel":
            cur.execute("DELETE FROM channels WHERE channel=?", (text,))
            conn.commit()
            await update.message.reply_text("❌ O‘chirildi"); context.user_data.clear()
            return

        if text == "🗑 Kino o‘chirish":
            context.user_data["step"] = "del_movie"
            await update.message.reply_text("Kino kodini yuboring:")
            return
        
        if step == "del_movie":
            cur.execute("DELETE FROM movies WHERE code=?", (text,))
            conn.commit()
            await update.message.reply_text("🗑 O‘chirildi"); context.user_data.clear()
            return

        if text == "📢 Reklama":
            cur.execute("SELECT COUNT(*) FROM users"); total = cur.fetchone()[0]
            context.user_data["step"] = "wait_limit"
            await update.message.reply_text(f"Jami user: {total}\nNechta odamga yuboramiz? (0 = hammasi)")
            return

        if step == "wait_limit":
            if text.isdigit():
                context.user_data["limit"] = int(text)
                context.user_data["step"] = "wait_ads"
                await update.message.reply_text("Reklama xabarini yuboring:")
            else: await update.message.reply_text("Faqat son yozing")
            return

        if step == "wait_ads":
            await send_ads(update, context)
            return

    # USER QIDIRUV
    if text and not text.startswith("/"):
        cur.execute("SELECT file_id, name, views FROM movies WHERE code=?", (text,))
        movie = cur.fetchone()
        if movie:
            cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (text,))
            conn.commit()
            await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}\n👁 {movie[2]+1}")
        else: await update.message.reply_text("❌ Kino topilmadi")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, messages))
    print("🚀 BOT ISHLADI!")
    app.run_polling()

if __name__ == "__main__":
    main()
