import os
import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()

# --- SERVER QISMI ---
@app.get("/win")
async def serve_index(request: Request, id: str):
    # Bu yerda index.html faylini yuboramiz
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    else:
        return HTMLResponse("Fayl topilmadi. Iltimos, index.html yuklanganini tekshiring.")

@app.get("/")
async def health():
    return {"status": "active"}

# --- BOT QISMI ---
@dp.message(Command("start"))
async def start_cmd(m: types.Message):
    # Railway domeningizni avtomatik aniqlashga harakat qilamiz
    # Agar sizda domen bo'lsa, uni pastdagi o'zgaruvchiga yozib qo'ygan ma'qul
    # Lekin biz hozircha Railway networking URL'ingizni kutyapmiz
    
    # DIQQAT: Railway Settings -> Networking'dan olgan domeningizni bura yozing:
    MY_DOMAIN = "botmeniki-sarikprok.up.railway.app" 
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 50,000 SO'M OLISH", url=f"https://{MY_DOMAIN}/win?id={m.from_user.id}")]
    ])
    
    await m.answer(
        f"Salom {m.from_user.first_name}!\n\nSizga 50,000 so'm yutuq chiqdi. Uni yechib olish uchun pastdagi tugmani bosing:",
        reply_markup=kb
    )

async def run_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Botni fonda ishga tushirish
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    # Serverni ishga tushirish
    uvicorn.run(app, host="0.0.0.0", port=port)
