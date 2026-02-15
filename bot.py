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

# ================= START (TEKSHIRUV TUZATILDI) =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Userni bazaga yozish
    cur.execute("INSERT OR REPLACE INTO users VALUES(?,?)", (str(user_id), user.username or "NoName"))
    conn.commit()

    is_callback = update.callback_query is not None
    target_msg = update.callback_query.message if is_callback else update.message

    # Admin bo'lsa
    if user_id == ADMIN_ID:
        if is_callback: await update.callback_query.answer()
        await target_msg.reply_text("🔥 ADMIN PANEL", reply_markup=admin_keyboard())
        return

    # Kanallarni olish
    cur.execute("SELECT channel FROM channels")
    all_channels = [i[0] for i in cur.fetchall()]
    
    not_joined = []
    
    for ch in all_channels:
        # FAQAT @ BILAN BOSHLANGANLARNI TEKSHIRAMIZ
        if ch.startswith("@"):
            try:
                member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    not_joined.append(ch)
            except Exception as e:
                # Agar bot kanalga admin bo'lmasa yoki kanal topilmasa
                print(f"Xato: {ch} ni tekshirib bo'lmadi: {e}")
                not_joined.append(ch)

    # Agar obuna bo'lmagan @ kanallar bo'lsa
    if not_joined:
        buttons = []
        for c in all_channels:
            url = f"https://t.me/{c[1:]}" if c.startswith("@") else c
            buttons.append([InlineKeyboardButton("📢 A'zo bo'lish", url=url)])
        
        buttons.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub")])
        
        if is_callback:
            await update.callback_query.answer("❌ Hali hamma kanallarga a'zo emassiz!", show_alert=True)
        else:
            await update.message.reply_text("Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # Obuna to'liq bo'lsa
    if is_callback:
        await update.callback_query.answer("✅ Rahmat!", show_alert=True)
        await update.callback_query.message.delete()
        await context.bot.send_message(user_id, "🎬 Kino kodini yuboring:")
    else:
        await update.message.reply_text("🎬 Kino kodini yuboring:")

# ================= MESSAGE HANDLER =================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        # Video yuborilganda admin rejimida bo'lsa ishlashi kerak
        if update.effective_user.id == ADMIN_ID and context.user_data.get("step") in ["one_video", "batch_vids"]:
            pass
        else:
            return

    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if user_id == ADMIN_ID:
        # Kanal qo'shish qismi
        if text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_ch"
            await update.message.reply_text("Kanalni kiriting:\n\n1. Tekshiriladigan bo'lsa: `@kanal_nomi`\n2. Shunchaki link bo'lsa: `https://t.me/...` ko'rinishida yuboring.")
            return
        
        if step == "add_ch" and text:
            cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (text,))
            conn.commit()
            await update.message.reply_text(f"✅ Kanal qo'shildi: {text}", reply_markup=admin_keyboard())
            context.user_data.clear()
            return
        
        # Boshqa admin buyruqlari (O'chirish, Statistika, Kino qo'shish)
        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "one_video"
            await update.message.reply_text("Kino videosini yuboring:"); return
        if step == "one_video" and update.message.video:
            context.user_data["f_id"] = update.message.video.file_id
            context.user_data["step"] = "one_code"
            await update.message.reply_text("Kino kodini yozing:"); return
        if step == "one_code" and text:
            context.user_data["code"] = text
            context.user_data["step"] = "one_name"
            await update.message.reply_text("Kino nomini yozing:"); return
        if step == "one_name" and text:
            cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?,0)", (context.user_data["code"], context.user_data["f_id"], text))
            conn.commit()
            await update.message.reply_text("✅ Saqlandi!", reply_markup=admin_keyboard()); context.user_data.clear(); return

        if text == "📦 Ommaviy qo‘shish":
            context.user_data["step"] = "batch_codes"
            await update.message.reply_text("Kodlarni probel bilan yuboring (Masalan: 1 2 3):"); return
        if step == "batch_codes" and text:
            codes = re.findall(r'\d+', text)
            context.user_data["b_codes"] = codes
            context.user_data["step"] = "batch_vids"
            await update.message.reply_text(f"✅ {len(codes)} ta kod. Videolarni yuboring."); return
        if step == "batch_vids" and update.message.video:
            codes = context.user_data.get("b_codes", [])
            if codes:
                c = codes.pop(0)
                cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?,0)", (c, update.message.video.file_id, f"Kino {c}"))
                conn.commit()
                if codes: await update.message.reply_text(f"✅ {c} saqlandi. Yana {len(codes)} ta...");
                else: await update.message.reply_text("🎉 Tugadi!", reply_markup=admin_keyboard()); context.user_data.clear();
            return
            
        if text == "📊 Statistika":
            cur.execute("SELECT COUNT(*) FROM users"); u = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM movies"); m = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM channels"); c = cur.fetchone()[0]
            await update.message.reply_text(f"📊 STATISTIKA\n👤 Userlar: {u}\n🎬 Kinolar: {m}\n📢 Kanallar: {c}"); return

        if text == "❌ Kanal o‘chirish":
            context.user_data["step"] = "del_ch"; await update.message.reply_text("O'chiriladigan kanalni kiriting:"); return
        if step == "del_ch" and text:
            cur.execute("DELETE FROM channels WHERE channel=?", (text,)); conn.commit()
            await update.message.reply_text("❌ Kanal o'chirildi!", reply_markup=admin_keyboard()); context.user_data.clear(); return

        if text == "🗑 Kino o‘chirish":
            context.user_data["step"] = "del_m"; await update.message.reply_text("Kino kodini yuboring:"); return
        if step == "del_m" and text:
            cur.execute("DELETE FROM movies WHERE code=?", (text,)); conn.commit()
            await update.message.reply_text("🗑 O'chirildi!"); context.user_data.clear(); return

    # --- USER QIDIRUV ---
    if text and not text.startswith("/"):
        cur.execute("SELECT file_id, name, views FROM movies WHERE code=?", (text,))
        movie = cur.fetchone()
        if movie:
            cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (text,))
            conn.commit()
            await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}\n👁 {movie[2]+1}")
        else:
            await update.message.reply_text("❌ Bunday kodli kino topilmadi.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, messages))
    print("🚀 BOT ISHLAYAPTI!")
    app.run_polling()

if __name__ == "__main__":
    main()
