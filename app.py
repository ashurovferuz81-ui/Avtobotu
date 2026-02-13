from flask import Flask, render_template
import sqlite3
import os

app = Flask(__name__)

def get_data():
    conn = sqlite3.connect("quran_ai.db")
    cur = conn.cursor()
    cur.execute("SELECT title, file_id, genre FROM lessons")
    movies = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]
    conn.close()
    return movies, users

@app.route('/')
def index():
    movies, user_count = get_data()
    return render_template('index.html', movies=movies, user_count=user_count)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
