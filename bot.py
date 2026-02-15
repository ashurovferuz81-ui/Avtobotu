import sqlite3
import nest_asyncio
import asyncio
import re
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
        ["🎬 Kino qo‘shish", "📦 Ommaviy qo‘shish"],
        ["🗑 Kino o‘chirish", "📊 Statistika"],
        ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
        ["👥 Userlar", "📢 Reklama"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or "NoName"

    cur.execute("INSERT OR REPLACE INTO users VALUES(?,?)", (user_id, username))
    conn.commit()

    target = update.message if update.message else update.callback_query.message

    if int(user_id) == ADMIN_ID:
        await target.reply_text("🔥 ADMIN PANEL", reply_markup=admin_keyboard())
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

# ================= REKLAMA =================
async def send_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = context.user_data.get("limit")
    cur.execute(f"SELECT user_id FROM users LIMIT {int(limit)}" if limit and limit > 0 else "SELECT user_id FROM users")
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
        # --- 1. ODDIY KINO QO'SHISH (Bitta-bitta) ---
        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "one_video"
            await update.message.reply_text("Kino videosini yuboring:")
            return

        if step == "one_video" and update.message.video:
            context.user_data["f_id"] = update.message.video.file_id
            context.user_data["step"] = "one_code"
            await update.message.reply_text("Kino kodini yozing:")
            return

        if step == "one_code":
            context.user_data["code"] = text
            context.user_data["step"] = "one_name"
            await update.message.reply_text("Kino nomini yozing:")
            return

        if step == "one_name":
            cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?,0)", (context.user_data["code"], context.user_data["f_id"], text))
            conn.commit()
            await update.message.reply_text("✅ Kino saqlandi!", reply_markup=admin_keyboard())
            context.user_data.clear()
            return

        # --- 2. OMMAVIY QO'SHISH ---
        if text == "📦 Ommaviy qo‘shish":
            context.user_data["step"] = "batch_codes"
            await update.message.reply_text("Kodlarni probel bilan yuboring (Masalan: 10 11 12):")
            return

        if step == "batch_codes":
            codes = re.findall(r'\d+', text)
            if not codes:
                await update.message.reply_text("Son topilmadi!")
                return
            context.user_data["b_codes"] = codes
            context.user_data["step"] = "batch_vids"
            await update.message.reply_text(f"✅ {len(codes)} ta kod qabul qilindi. Videolarni ketma-ket yuboring.")
            return

        if step == "batch_vids" and update.message.video:
            codes = context.user_data.get("b_codes", [])
            if codes:
                c = codes.pop(0)
                cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?,0)", (c, update.message.video.file_id, f"Kino {c}"))
                conn.commit()
                if codes:
                    context.user_data["b_codes"] = codes
                    await update.message.reply_text(f"✅ {c} saqlandi. Yana {len(codes)} ta...")
                else:
                    await update.message.reply_text("🎉 Hammasi tugadi!", reply_markup=admin_keyboard())
                    context.user_data.clear()
            return

        # --- ADMIN BOSHQARUV ---
        if text == "📊 Statistika":
            cur.execute("SELECT COUNT(*) FROM users"); u = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM movies"); m = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM channels"); c = cur.fetchone()[0]
            await update.message.reply_text(f"📊 STATISTIKA\n\n👤 Userlar: {u}\n🎬 Kinolar: {m}\n📢 Kanallar: {c}")
            return

        if text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_ch"; await update.message.reply_text("Kanal @username yuboring:"); return
        
        if step == "add_ch":
            cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (text,)); conn.commit()
            await update.message.reply_text("✅ Qo'shildi"); context.user_data.clear(); return

        if text == "❌ Kanal o‘chirish":
            context.user_data["step"] = "del_ch"; await update.message.reply_text("Kanal @username yuboring:"); return
        
        if step == "del_ch":
            cur.execute("DELETE FROM channels WHERE channel=?", (text,)); conn.commit()
            await update.message.reply_text("❌ O'chirildi"); context.user_data.clear(); return

        if text == "🗑 Kino o‘chirish":
            context.user_data["step"] = "del_m"; await update.message.reply_text("Kino kodini yuboring:"); return
        
        if step == "del_m":
            cur.execute("DELETE FROM movies WHERE code=?", (text,)); conn.commit()
            await update.message.reply_text("🗑 O'chirildi"); context.user_data.clear(); return

        if text == "📢 Reklama":
            cur.execute("SELECT COUNT(*) FROM users"); total = cur.fetchone()[0]
            context.user_data["step"] = "wait_lim"
            await update.message.reply_text(f"Jami user: {total}\nNechta odamga yuboramiz? (0 = hammasi)")
            return

        if step == "wait_lim":
            if text.isdigit():
                context.user_data["limit"] = int(text)
                context.user_data["step"] = "wait_ad"
                await update.message.reply_text("Reklama xabarini yuboring:")
            else: await update.message.reply_text("Faqat son yozing")
            return

        if step == "wait_ad":
            await send_ads(update, context); return

    # USER QIDIRUV
    if text and not text.startswith("/"):
        cur.execute("SELECT file_id, name, views FROM movies WHERE code=?", (text,))
        movie = cur.fetchone()
        if movie:
            cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (text,))
            conn.commit()
            await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}\n👁 {movie[2]+1}")
        else: await update.message.reply_text("❌ Kino topilmadi")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, messages))
    print("🚀 BOT TAYYOR!")
    app.run_polling()

if __name__ == "__main__":
    main()
