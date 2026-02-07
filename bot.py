from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

MAIN_BOT_TOKEN = "6620108420:AAH85e63iY7dZ9KI_DYP686OOL9buqrdAQk"
ADMIN_ID = 5775388579

# --- Bazalar ---
user_bots = {}       # user_id -> token
channels = {}        # user_id -> obuna bo'lish kerak bo'lgan kanal
user_subscribed = {} # user_id -> True/False
movies = {}          # user_id -> list of kino dicts [{'name':'Avatar','video_id':12345,'desc':'...'}]

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in channels:
        keyboard = [
            [InlineKeyboardButton("📢 Majburiy Obuna", callback_data="subscribe")],
        ]
        await update.message.reply_text("Salom! Kino bot ishlashi uchun obuna bo‘ling:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Obuna bo'lgan foydalanuvchi
    keyboard = [
        [InlineKeyboardButton("🎬 Kino qo‘shish", callback_data="add_movie")],
        [InlineKeyboardButton("📺 Obuna bo‘ldim", callback_data="check_sub")],
    ]
    await update.message.reply_text("Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Inline tugmalar ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # --- Majburiy obuna ---
    if data == "subscribe":
        await query.message.edit_text("Iltimos, kanal linkini yuboring:")
        context.bot_data['awaiting_channel'] = user_id
        return

    # --- Obuna bo'ldim tugmasi ---
    if data == "check_sub":
        if user_subscribed.get(user_id, False):
            await query.message.reply_text("✅ Siz obuna bo‘ldingiz! Endi kino kodini yuborishingiz mumkin.")
        else:
            await query.message.reply_text("❌ Obuna bo‘ling, keyin kino qo‘shishingiz mumkin.")
        return

    # --- Kino qo‘shish admin panel ---
    if data == "add_movie":
        await query.message.reply_text("Iltimos, kino nomini kiriting:")
        context.bot_data['awaiting_movie_name'] = user_id
        return

# --- Foydalanuvchi ma’lumot yuboradi ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Kanal yuborish
    if context.bot_data.get('awaiting_channel') == user_id:
        channels[user_id] = text
        user_subscribed[user_id] = False
        await update.message.reply_text(f"Kanal saqlandi: {text}\nEndi obuna bo‘lishingiz kerak.")
        del context.bot_data['awaiting_channel']
        return

    # Kino nomi
    if context.bot_data.get('awaiting_movie_name') == user_id:
        context.bot_data['temp_movie_name'] = text
        await update.message.reply_text("Endi kino video ID sini yuboring:")
        del context.bot_data['awaiting_movie_name']
        context.bot_data['awaiting_movie_video'] = user_id
        return

    # Kino video ID
    if context.bot_data.get('awaiting_movie_video') == user_id:
        movie_name = context.bot_data.pop('temp_movie_name', "NoName")
        movie_video = text
        movies.setdefault(user_id, []).append({'name': movie_name, 'video_id': movie_video})
        await update.message.reply_text(f"✅ Kino qo‘shildi: {movie_name}")
        del context.bot_data['awaiting_movie_video']
        return

# --- APPLICATION ---
app = ApplicationBuilder().token(MAIN_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🔥 Kino Bot Admin Panel va Majburiy Obuna ishga tushdi!")
app.run_polling()
