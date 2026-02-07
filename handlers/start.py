from telegram import Update
from telegram.ext import ContextTypes
from database import add_user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)

    await update.message.reply_text(
        "🎧 Istalgan qo‘shiq nomini yozing va men topib beraman!\n\nAdmin panel mavjud ✅"
    )
