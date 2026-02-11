import os
import sqlite3
import requests
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

# Bot Token and Admin ID
BOT_TOKEN = '8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA'
ADMIN_ID = 5775388579

# Initialize bot
bot = Bot(BOT_TOKEN)
updater = Updater(BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# SQLite Database (SQLite file storage, no external DB)
DB_PATH = "bot_db.sqlite"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Initialize database if not exists
def init_db():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        step TEXT,
        ban INTEGER,
        lastmsg TEXT,
        sana TEXT
    );
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kino INTEGER,
        kino2 INTEGER
    );
    ''')
    conn.commit()

# Helper function to send messages
def send_message(chat_id, text):
    bot.send_message(chat_id, text, parse_mode='HTML')

# Command: /start
def start(update, context):
    user_id = update.message.chat_id
    first_name = update.message.chat.first_name
    last_name = update.message.chat.last_name
    now = datetime.now().strftime("%d-%m-%Y %H:%M")

    # Check if user exists in DB, if not, insert them
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, first_name, last_name, step, ban, lastmsg, sana) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       (user_id, first_name, last_name, "0", 0, "start", now))
        conn.commit()

    cursor.execute("UPDATE users SET sana=? WHERE user_id=?", (now, user_id))
    conn.commit()
    
    # Send welcome message
    send_message(user_id, f"Hello {first_name}, welcome to the bot!")

# Handle messages
def handle_message(update, context):
    user_id = update.message.chat_id
    text = update.message.text

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        send_message(user_id, "You are not registered. Please start the bot with /start.")
        return
    
    step = user[3]
    
    # If user is banned
    if user[4] == 1:
        send_message(user_id, "You are banned from using this bot.")
        return

    if text == "/start":
        start(update, context)
    else:
        send_message(user_id, f"You sent: {text}")

# Handle callback query
def handle_callback_query(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    # Responding to callback queries
    if data == "start":
        start(update, context)
        query.answer()

# Initialize DB
init_db()

# Handlers
start_handler = CommandHandler('start', start)
message_handler = MessageHandler(Filters.text & ~Filters.command, handle_message)
callback_query_handler = CallbackQueryHandler(handle_callback_query)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(message_handler)
dispatcher.add_handler(callback_query_handler)

# Start the bot
updater.start_polling()
updater.idle()
