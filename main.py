import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# -------------------
MAIN_BOT_TOKEN = "6620108420:AAH85e63iY7dZ9KI_DYP686OOL9buqrdAQk"
ADMIN_ID = 5775388579
# -------------------

# Bazalar
user_bots = {}        # user_id -> token
user_apps = {}        # user_id -> ApplicationBuilder object
user_premium = {}     # user_id -> True/False

# -------------------
# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📊 Foydalanuvchi Botlari", callback_data="admin_stats")],
            [InlineKeyboardButton("⭐ Premium berish", callback_data="admin_premium")]
        ]
        await update.message.reply_text("⚡ Admin panelga xush kelibsiz!", reply_markup=InlineKeyboardMarkup(keyboard))
        return

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
        await query.message.edit_text("🎬 Iltimos, foydalanuvchi bot tokenini yuboring:")
        context.bot_data['awaiting_token'] = user_id
        return

    # Admin: foydalanuvchi botlari statistikasi
    if data == "admin_stats" and user_id == ADMIN_ID:
        msg = f"📊 Foydalanuvchi botlari: {len(user_bots)} ta\n"
        for uid, token in user_bots.items():
            prem = "✅" if user_premium.get(uid, False) else "❌"
            msg += f"ID: {uid}, Premium: {prem}\n"
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
        # Token saqlash
        user_bots[user_id] = text
        await update.message.reply_text("✅ Token qabul qilindi! Sizning kino botingiz ishga tushadi.")
        del context.bot_data['awaiting_token']

        # Dinamik foydalanuvchi botini ishga tushirish
        await start_user_bot(user_id, text)
        return

# -------------------
# Dinamik foydalanuvchi botini ishga tushirish
async def start_user_bot(user_id, token):
    app = ApplicationBuilder().token(token).build()
    user_apps[user_id] = app

    # Kino bot /start handler
    async def user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🎬 Kino qo‘shish", callback_data="add_movie")],
            [InlineKeyboardButton("📺 Premium tekshirish", callback_data="check_premium")]
        ]
        await update.message.reply_text("Salom! Kino bot ishga tushdi:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Inline tugmalar foydalanuvchi botida
    async def user_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        uid = query.from_user.id
        if query.data == "check_premium":
            if user_premium.get(uid, False):
                await query.message.reply_text("✅ Siz premium foydalanuvchisiz!")
            else:
                await query.message.reply_text("❌ Siz premium foydalanuvchi emassiz!")

        if query.data == "add_movie":
            if uid != user_id:
                await query.message.reply_text("❌ Faqat admin kino qo‘shishi mumkin!")
                return
            await query.message.reply_text("🎬 Kino nomini yuboring:")
            context.bot_data['awaiting_movie_name'] = uid

    # Matn handler (kino nomi va video)
    async def user_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        text = update.message.text.strip()

        if context.bot_data.get('awaiting_movie_name') == uid:
            context.bot_data['temp_movie_name'] = text
            await update.message.reply_text("Iltimos, kino video linkini yuboring:")
            del context.bot_data['awaiting_movie_name']
            context.bot_data['awaiting_movie_video'] = uid
            return

        if context.bot_data.get('awaiting_movie_video') == uid:
            movie_name = context.bot_data.pop('temp_movie_name', "NoName")
            movie_video = text
            if 'movies' not in context.bot_data:
                context.bot_data['movies'] = []
            context.bot_data['movies'].append({'name': movie_name, 'video': movie_video})
            await update.message.reply_text(f"✅ Kino qo‘shildi: {movie_name}")
            del context.bot_data['awaiting_movie_video']
            return

    app.add_handler(CommandHandler("start", user_start))
    app.add_handler(CallbackQueryHandler(user_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_text))

    # Botni alohida asyncio task sifatida ishga tushirish
    asyncio.create_task(app.run_polling())

# -------------------
# Asosiy app
app = ApplicationBuilder().token(MAIN_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🔥 Asosiy bot ishga tushdi!")
app.run_polling()
