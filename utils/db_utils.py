import sqlite3

# Ma'lumotlar bazasi bilan bog'lanish
conn = sqlite3.connect("database.db", check_same_thread=False)
cur = conn.cursor()

# Kinolarni qo‘shish, o‘chirish va olish
def add_movie(code, file_id, name):
    cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?)", (code, file_id, name))
    conn.commit()

def del_movie(code):
    cur.execute("DELETE FROM movies WHERE code=?", (code,))
    conn.commit()

def get_movie(code):
    cur.execute("SELECT file_id,name FROM movies WHERE code=?", (code,))
    return cur.fetchone()

# Kanallarni qo‘shish, o‘chirish va olish
def add_channel(channel):
    cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (channel,))
    conn.commit()

def del_channel(channel):
    cur.execute("DELETE FROM channels WHERE channel=?", (channel,))
    conn.commit()

def get_all_channels():
    cur.execute("SELECT channel FROM channels")
    return [i[0] for i in cur.fetchall()]

# Foydalanuvchilarni qo‘shish va olish
def add_user(user_id, username):
    cur.execute("INSERT OR IGNORE INTO users VALUES(?,?)", (user_id, username))
    conn.commit()

def get_all_users():
    cur.execute("SELECT user_id, username FROM users")
    return cur.fetchall()

# Kinolar reytingi va top kinolarni olish
def get_top_rated_movies():
    cur.execute("SELECT code, name, views FROM movies ORDER BY views DESC LIMIT 5")
    return cur.fetchall()

def get_random_movie():
    cur.execute("SELECT file_id, name FROM movies ORDER BY RANDOM() LIMIT 1")
    return cur.fetchone()

# Kinolarni necha kishi ko‘rganini qaytarish
def update_views(code):
    cur.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (code,))
    conn.commit()
