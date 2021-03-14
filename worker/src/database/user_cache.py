import redis

user_set = 'user_ids'


def add_user(user_id: str, redis_cache):
    redis_cache.sadd(user_set, user_id)


def user_exists(user_id: str, redis_cache) -> bool:
    return redis_cache.sismember(user_set, user_id)
