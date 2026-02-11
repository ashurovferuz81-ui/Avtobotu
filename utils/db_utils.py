import psycopg2

DATABASE_URL = "postgresql://postgres:dlWNyapkcvkRlBwgxHpFMvUkRBjBxGKe@postgres.railway.internal:5432/railway"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ==== TABLES ==== #
def create_tables():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS movies(
        code TEXT PRIMARY KEY,
        file_id TEXT,
        name TEXT
    )""")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS channels(
        channel_id TEXT PRIMARY KEY
    )""")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id TEXT PRIMARY KEY,
        username TEXT
    )""")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS movie_views(
        user_id TEXT,
        movie_code TEXT,
        PRIMARY KEY(user_id, movie_code)
    )""")
    conn.commit()

# ==== MOVIES ==== #
def add_movie(code, file_id, name):
    cur.execute("INSERT INTO movies(code,file_id,name) VALUES(%s,%s,%s) ON CONFLICT (code) DO UPDATE SET file_id=%s,name=%s",
                (code, file_id, name, file_id, name))
    conn.commit()

def del_movie(code):
    cur.execute("DELETE FROM movies WHERE code=%s", (code,))
    conn.commit()

def get_movie(code):
    cur.execute("SELECT file_id,name FROM movies WHERE code=%s", (code,))
    return cur.fetchone()

def get_all_movies():
    cur.execute("SELECT code,name FROM movies")
    return cur.fetchall()

# ==== CHANNELS ==== #
def add_channel(channel):
    cur.execute("INSERT INTO channels(channel_id) VALUES(%s) ON CONFLICT DO NOTHING", (channel,))
    conn.commit()

def del_channel(channel):
    cur.execute("DELETE FROM channels WHERE channel_id=%s", (channel,))
    conn.commit()

def get_all_channels():
    cur.execute("SELECT channel_id FROM channels")
    return [i[0] for i in cur.fetchall()]

# ==== USERS ==== #
def add_user(user_id, username):
    cur.execute("INSERT INTO users(user_id,username) VALUES(%s,%s) ON CONFLICT DO NOTHING", (user_id, username))
    conn.commit()

def get_all_users():
    cur.execute("SELECT user_id,username FROM users")
    return cur.fetchall()

# ==== MOVIE VIEWS ==== #
def add_movie_view(user_id, movie_code):
    try:
        cur.execute("INSERT INTO movie_views(user_id,movie_code) VALUES(%s,%s) ON CONFLICT DO NOTHING", (user_id, movie_code))
        conn.commit()
    except:
        pass

def get_movie_views_count(movie_code):
    cur.execute("SELECT COUNT(*) FROM movie_views WHERE movie_code=%s", (movie_code,))
    return cur.fetchone()[0]

def get_top_movies(limit=5):
    cur.execute("""
    SELECT m.code,m.name,COUNT(v.user_id) as views
    FROM movies m
    LEFT JOIN movie_views v ON m.code=v.movie_code
    GROUP BY m.code,m.name
    ORDER BY views DESC
    LIMIT %s
    """, (limit,))
    return cur.fetchall()
