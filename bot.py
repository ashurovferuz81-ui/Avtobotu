import os
import logging
import asyncio
from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
# Railway domeningizni bura yozing
BASE_URL = "https://botmeniki-sarikprok.up.railway.app"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()

# --- SERVER QISMI ---
@app.get("/win")
async def serve_index(id: str):
    # index.html faylini ko'rsatish
    return FileResponse("index.html")

@app.get("/")
async def health():
    return {"status": "ok"}

# --- BOT QISMI ---
@dp.message(Command("start"))
async def start_cmd(m: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 50,000 SO'M OLISH", url=f"{BASE_URL}/win?id={m.from_user.id}")]
    ])
    await m.answer(
        f"Salom {m.from_user.first_name}!\n\nSizga 50,000 so'm yutuq chiqdi. Uni yechib olish uchun pastdagi tugmani bosing:",
        reply_markup=kb
    )

async def run_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Railway PORTini olish
    port = int(os.environ.get("PORT", 8000))
    # Botni orqa fonda ishga tushirish
    asyncio.get_event_loop().create_task(run_bot())
    # Serverni ishga tushirish
    uvicorn.run(app, host="0.0.0.0", port=port)
