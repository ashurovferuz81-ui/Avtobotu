from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# -------------------
# Foydalanuvchi bot tokeni (foydalanuvchi o'z botini ishlatadi)
USER_BOT_TOKEN = "SIZNING_FOYDALANUVCHI_BOT_TOKENI"
# Admin ID foydalanuvchi o'z telegram ID sini yozadi
ADMIN_ID = None  # Masalan: 123456789
# Kanal majburiy obuna (foydalanuvchi botiga)
CHANNEL_ID = None  # Masalan: -1001234567890
# -------------------

# Bazalar
movies = []           # [{'name':'Avatar','video':'link'}]
premium_users = set() # premium foydalanuvchilar
subscribed_users = set() # kanalga obuna bo'lganlar

# -------------------
# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("🎬 Kino qo‘shish", callback_data="add_movie")],
        [InlineKeyboardButton("📺 Premium tekshirish", callback_data="check_premium")],
        [InlineKeyboardButton("📢 Majburiy obuna tekshirish", callback_data="check_subscribe")]
    ]
    await update.message.reply_text("Salom! Kino botga xush kelibsiz:", reply_markup=InlineKeyboardMarkup(keyboard))

# -------------------
# Inline tugmalar
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Kino qo'shish (faqat admin foydalanuvchi)
    if data == "add_movie":
        if user_id != ADMIN_ID:
            await query.message.reply_text("❌ Siz kino qo‘sholmaysiz!")
            return
        await query.message.reply_text("🎬 Iltimos, kino nomini yuboring:")
        context.bot_data['awaiting_movie_name'] = user_id
        return

    # Premium tekshirish
    if data == "check_premium":
        if user_id in premium_users:
            await query.message.reply_text("✅ Siz premium foydalanuvchisiz! Kino videolarini ko‘rishingiz mumkin.")
        else:
            await query.message.reply_text("❌ Siz premium foydalanuvchi emassiz!")
        return

    # Majburiy obuna tekshirish
    if data == "check_subscribe":
        if CHANNEL_ID is None:
            await query.message.reply_text("⚠️ Kanal hali sozlanmagan.")
            return
        # Bu yerda Telegram API orqali foydalanuvchi obunasi tekshirilishi mumkin
        if user_id in subscribed_users:
            await query.message.reply_text("✅ Siz kanalga obuna bo‘lgansiz!")
        else:
            await query.message.reply_text("❌ Obuna bo‘ling, keyin kino videolarini ko‘rishingiz mumkin.")
        return

# -------------------
# Matn qabul qilish (kino nomi va video linki)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Kino nomi
    if context.bot_data.get('awaiting_movie_name') == user_id:
        context.bot_data['temp_movie_name'] = text
        await update.message.reply_text("Iltimos, kino video linkini yuboring:")
        del context.bot_data['awaiting_movie_name']
        context.bot_data['awaiting_movie_video'] = user_id
        return

    # Kino video linki
    if context.bot_data.get('awaiting_movie_video') == user_id:
        movie_name = context.bot_data.pop('temp_movie_name', "NoName")
        movie_video = text
        movies.append({'name': movie_name, 'video': movie_video})
        await update.message.reply_text(f"✅ Kino qo‘shildi: {movie_name}")
        del context.bot_data['awaiting_movie_video']
        return

# -------------------
# Asosiy application
app = ApplicationBuilder().token(USER_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🔥 Foydalanuvchi kino bot ishga tushdi!")
app.run_polling()
