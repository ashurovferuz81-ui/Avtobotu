import os
from telegram import Update
from telegram.ext import ContextTypes
from downloader import download_song
from cache import get_cached, set_cache

async def music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()

    cached = get_cached(query)

    if cached:
        await update.message.reply_audio(cached)
        return

    msg = await update.message.reply_text("⚡ Yuklanmoqda...")

    file = download_song(query)

    audio = await update.message.reply_audio(audio=open(file, "rb"))

    set_cache(query, audio.audio.file_id)

    os.remove(file)

    await msg.delete()
