import json
from app.core.redis import redis_client

ROOMS_CACHE_KEY = "vastu_rooms"
OBJECTS_CACHE_KEY = "vastu_objects"
def get_cached_rules():
    data = redis_client.get("vastu_rules")
    if data:
        return json.loads(data)
    return None


def set_cached_rules(rules):
    redis_client.set(
        "vastu_rules",
        json.dumps(rules),
        ex=3600  # 1 hour
    )


def invalidate_rules_cache():
    redis_client.delete("vastu_rules")

# -------- ROOMS --------

def get_cached_rooms():
    data = redis_client.get(ROOMS_CACHE_KEY)
    return json.loads(data) if data else None


def set_cached_rooms(room_list):
    redis_client.set(
        ROOMS_CACHE_KEY,
        json.dumps(room_list),
        ex=86400
    )


# -------- OBJECTS --------

def get_cached_objects():
    data = redis_client.get(OBJECTS_CACHE_KEY)
    return json.loads(data) if data else None


def set_cached_objects(object_list):
    redis_client.set(
        OBJECTS_CACHE_KEY,
        json.dumps(object_list),
        ex=86400
    )


def invalidate_dropdown_cache():
    redis_client.delete(ROOMS_CACHE_KEY)
    redis_client.delete(OBJECTS_CACHE_KEY)