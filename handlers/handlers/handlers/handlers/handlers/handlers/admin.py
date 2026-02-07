from telegram import Update
from telegram.ext import ContextTypes
from database import get_all_users, set_premium
from config import ADMIN_ID

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return

    text = "📊 Admin panel:\n\n"
    users = get_all_users()
    text += f"Foydalanuvchilar soni: {len(users)}\n\n"
    text += "Foydalanuvchi ID lar:\n"
    text += "\n".join(str(u[0]) for u in users)

    await update.message.reply_text(text)

async def make_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return

    if not context.args:
        await update.message.reply_text("Foydalanuvchi ID sini yozing.")
        return

    user_id = int(context.args[0])
    set_premium(user_id)
    await update.message.reply_text(f"✅ {user_id} Premium qilindi!")
