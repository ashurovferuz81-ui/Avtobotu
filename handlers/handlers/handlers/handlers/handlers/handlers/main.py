from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config import TOKEN
from handlers.start import start
from handlers.music import music
from handlers.admin import admin_panel, make_premium

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, music))

# Admin
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CommandHandler("premium", make_premium))

print("💥 SUPER PRO BOT ishga tushdi!")

app.run_polling()
