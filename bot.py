import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from utils.db_utils import *
from utils.sub_utils import not_subscribed
import random

nest_asyncio.apply()

# Token va Admin ID ni kiritish
TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579  # Avvalgi admin ID

# ===== ADMIN KEYBOARD =====
def admin_keyboard():
    keyboard = [
        ["🎬 Kino qo‘shish", "🗑 Kino o‘chirish"],
        ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
        ["👥 Userlar", "📊 Statistika"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== USER KEYBOARD =====
def user_keyboard():
    keyboard = [
        ["🎬 Kino topish", "📊 Reytingli kinolar", "🎲 Aralash Kino"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
        for ch in get_all_channels():
            if ch.startswith("@") or ch.startswith("https://"):
                url = f"https://t.me/{ch[1:]}" if ch.startswith("@") else ch
                buttons.append([InlineKeyboardButton("📢 Kanalga kirish", url=url)])
        buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")])
        await update.message.reply_text("📢 Kanallarga obuna bo‘ling:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    await update.message.reply_text("🎬 Kino kodini yuboring:", reply_markup=user_keyboard())

# ===== BUTTON =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    missing = await not_subscribed(query.from_user.id, context.bot)
    if missing:
        await query.answer("❌ Hali obuna bo‘lmagansiz!", show_alert=True)
        return
    await query.message.edit_text("✅ Endi kino kodini yuboring!")

# ===== VIDEO =====
async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.user_data.get("step") == "video":
        context.user_data["file"] = update.message.video.file_id
        context.user_data["step"] = "name"
        await update.message.reply_text("🎬 Kino nomini yozing:")

# ===== TEXT MESSAGES =====
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    # ===== ADMIN LOGIC =====
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
            # Kino statistikasini ko‘rish
            msg = "📊 Statistika:\n"
            for channel in get_all_channels():
                msg += f"\n{channel}:\n"
                for movie_code, movie_name in get_movie_stats(channel):
                    msg += f" - {movie_name} (kod: {movie_code})\n"
            await update.message.reply_text(msg, reply_markup=admin_keyboard())
            return

    # ===== USER LOGIC =====
    missing = await not_subscribed(user_id, context.bot)
    if missing:
        await update.message.reply_text("❌ Avval majburiy kanallarga obuna bo‘ling! /start bosing.")
        return
    if text == "🎬 Kino topish":
        await update.message.reply_text("🎬 Kino nomini yuboring:")
    elif text == "📊 Reytingli kinolar":
        # Reytingli kinolarni olish
        movies = get_top_rated_movies()
        if not movies:
            await update.message.reply_text("❌ Reytingli kinolar topilmadi!")
        else:
            for movie in movies:
                await update.message.reply_text(f"🎬 {movie[1]} - {movie[0]} (ko‘rildi: {movie[2]} marta)")
    elif text == "🎲 Aralash Kino":
        # Tasodifiy kino chiqarish
        movie = get_random_movie()
        if movie:
            await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}")
        else:
            await update.message.reply_text("❌ Tasodifiy kino topilmadi!")

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.VIDEO, video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))
    print("🔥 ULTRA ELITE BOT ISHLADI!")
    app.run_polling()

if __name__ == "__main__":
    main()
