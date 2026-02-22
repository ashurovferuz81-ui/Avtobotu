import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect("kino_system.db", check_same_thread=False)
        self.cur = self.conn.cursor()
        self.cur.execute("""CREATE TABLE IF NOT EXISTS my_bots (
            owner_id INTEGER PRIMARY KEY, 
            token TEXT, 
            is_premium INTEGER DEFAULT 0, 
            created_at TEXT, 
            sub_channel TEXT DEFAULT '@Sardorbeko008')""")
        self.cur.execute("CREATE TABLE IF NOT EXISTS movies (bot_token TEXT, code TEXT, file_id TEXT)")
        self.conn.commit()

    def add_bot(self, owner_id, token):
        date = datetime.now().strftime('%Y-%m-%d')
        self.cur.execute("INSERT OR REPLACE INTO my_bots (owner_id, token, created_at) VALUES (?, ?, ?)", (owner_id, token, date))
        self.conn.commit()

db = Database()
