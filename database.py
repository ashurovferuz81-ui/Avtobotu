import json
from pathlib import Path
from config import USERS_FILE

# users.json bo'lmasa yaratish
Path(USERS_FILE).parent.mkdir(exist_ok=True)
if not Path(USERS_FILE).exists():
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def add_user(user_id):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {"premium": False}
        save_users(users)

def set_premium(user_id):
    users = load_users()
    users[str(user_id)]["premium"] = True
    save_users(users)

def is_premium(user_id):
    users = load_users()
    return users.get(str(user_id), {}).get("premium", False)
