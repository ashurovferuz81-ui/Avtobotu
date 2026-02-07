import redis
from config import REDIS_URL

r = redis.Redis.from_url(REDIS_URL)

def get_cached(song):
    return r.get(song)

def set_cache(song, file_id):
    r.set(song, file_id)
