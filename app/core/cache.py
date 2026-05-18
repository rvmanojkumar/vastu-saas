import json
from app.core.redis import redis_client


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