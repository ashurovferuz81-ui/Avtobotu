from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- Sizning bot tokeningiz ---
MAIN_BOT_TOKEN = "6620108420:AAH85e63iY7dZ9KI_DYP686OOL9buqrdAQk"
ADMIN_ID = 5775388579

# --- Bazalar ---
user_bots = {}        # user_id -> foydalanuvchi bot tokeni
user_movies = {}      # user_id -> list [{'name':'Avatar','video':'link'}]
user_channels = {}    # user_id -> majburiy obuna kanali
user_subscribed = {}  # user_id -> True/False

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📊 Foydalanuvchi Botlari Statistikasi", callback_data="admin_stats")],
            [InlineKeyboardButton("⭐ Premium berish", callback_data="admin_premium")]
        ]
        await update.message.reply_text("⚡ Admin panelga xush kelibsiz!", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Foydalanuvchi menyusi
    keyboard = [
        [InlineKeyboardButton("🎬 Kino Bot yaratish", callback_data="create_cinema")],
        [InlineKeyboardButton("📢 Majburiy Obuna", callback_data="subscribe")],
        [InlineKeyboardButton("📺 Obuna bo‘ldim", callback_data="check_sub")]
    ]
    await update.message.reply_text("Salom! Tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Inline tugmalar ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # --- Foydalanuvchi: Kino bot yaratish ---
    if data == "create_cinema":
        await query.message.edit_text("🎬 Kino bot yaratish.\nIltimos, bot tokenini yuboring:")
        context.bot_data['awaiting_user_token'] = user_id
        return

    # --- Foydalanuvchi: Majburiy obuna ---
    if data == "subscribe":
        await query.message.edit_text("Iltimos, kanal linkini yuboring:")
        context.bot_data['awaiting_channel'] = user_id
        return

    # --- Foydalanuvchi: Obuna bo‘ldim tugmasi ---
    if data == "check_sub":
        if user_subscribed.get(user_id, False):
            await query.message.reply_text("✅ Siz obuna bo‘ldingiz! Endi kino qo‘shishingiz mumkin.")
        else:
            await query.message.reply_text("❌ Obuna bo‘ling, keyin kino qo‘shishingiz mumkin.")
        return

    # --- Admin panel: foydalanuvchi statistikasi ---
    if data == "admin_stats" and user_id == ADMIN_ID:
        msg = f"📊 Foydalanuvchi botlari: {len(user_bots)} ta\n"
        for uid, token in user_bots.items():
            msg += f"ID: {uid}, Token: {token}\n"
        await query.message.edit_text(msg)
        return

    # --- Admin panel: Premium berish ---
    if data == "admin_premium" and user_id == ADMIN_ID:
        buttons = [[InlineKeyboardButton(str(uid), callback_data=f"make_premium:{uid}")] for uid in user_bots.keys()]
        await query.message.edit_text("Premium beriladigan foydalanuvchini tanlang:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("make_premium:") and user_id == ADMIN_ID:
        uid = int(data.split(":")[1])
        user_subscribed[uid] = True
        await query.message.edit_text(f"✅ Foydalanuvchi {uid} ga premium berildi!")
        return

# --- Matn qabul qilish (token, kino nomi, kanal linki) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Foydalanuvchi bot tokeni
    if context.bot_data.get('awaiting_user_token') == user_id:
        user_bots[user_id] = text
        await update.message.reply_text(f"✅ Bot token qabul qilindi! Endi kino qo‘shishingiz mumkin.")
        del context.bot_data['awaiting_user_token']
        return

    # Majburiy obuna kanali
    if context.bot_data.get('awaiting_channel') == user_id:
        user_channels[user_id] = text
        user_subscribed[user_id] = False
        await update.message.reply_text(f"Kanal saqlandi: {text}\nEndi obuna bo‘lishingiz kerak.")
        del context.bot_data['awaiting_channel']
        return

# --- APPLICATION ---
app = ApplicationBuilder().token(MAIN_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🔥 Bot yaratadigan bot ishga tushdi!")
app.run_polling()
