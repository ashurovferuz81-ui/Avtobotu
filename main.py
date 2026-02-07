from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# -------------------
MAIN_BOT_TOKEN = "6620108420:AAH85e63iY7dZ9KI_DYP686OOL9buqrdAQk"
ADMIN_ID = 5775388579
# -------------------

# Bazalar
user_bots = {}        # user_id -> token
user_premium = {}     # user_id -> True/False
user_subscribed = {}  # user_id -> True/False

# -------------------
# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        # Faqat admin uchun panel
        keyboard = [
            [InlineKeyboardButton("📊 Foydalanuvchi Botlari", callback_data="admin_stats")],
            [InlineKeyboardButton("⭐ Premium berish", callback_data="admin_premium")]
        ]
        await update.message.reply_text("⚡ Admin panelga xush kelibsiz!", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Oddiy foydalanuvchi uchun menyu
    keyboard = [
        [InlineKeyboardButton("🎬 Kino bot yaratish", callback_data="create_cinema")]
    ]
    await update.message.reply_text("Salom! Kino bot yaratish uchun tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

# -------------------
# Inline tugmalar
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Foydalanuvchi: kino bot yaratish
    if data == "create_cinema":
        await query.message.edit_text("🎬 Kino bot yaratish.\nIltimos, token yuboring:")
        context.bot_data['awaiting_token'] = user_id
        return

    # Admin: foydalanuvchi botlari statistikasi
    if data == "admin_stats" and user_id == ADMIN_ID:
        msg = f"📊 Foydalanuvchi botlari: {len(user_bots)} ta\n"
        for uid, token in user_bots.items():
            prem = "✅" if user_premium.get(uid, False) else "❌"
            sub = "✅" if user_subscribed.get(uid, False) else "❌"
            msg += f"ID: {uid}, Premium: {prem}, Obuna: {sub}\n"
        await query.message.edit_text(msg)
        return

    # Admin: premium berish
    if data == "admin_premium" and user_id == ADMIN_ID:
        buttons = [[InlineKeyboardButton(str(uid), callback_data=f"make_premium:{uid}")] for uid in user_bots.keys()]
        await query.message.edit_text("Premium beriladigan foydalanuvchini tanlang:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("make_premium:") and user_id == ADMIN_ID:
        uid = int(data.split(":")[1])
        user_premium[uid] = True
        await query.message.edit_text(f"✅ Foydalanuvchi {uid} ga premium berildi!")
        return

# -------------------
# Matn qabul qilish (foydalanuvchi tokeni)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if context.bot_data.get('awaiting_token') == user_id:
        user_bots[user_id] = text
        await update.message.reply_text(f"✅ Token qabul qilindi! Sizning kino botingiz ishga tushadi.")
        del context.bot_data['awaiting_token']
        return

# -------------------
# Asosiy app
app = ApplicationBuilder().token(MAIN_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🔥 Asosiy bot ishga tushdi!")
app.run_polling()
