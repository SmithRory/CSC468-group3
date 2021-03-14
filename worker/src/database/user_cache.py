import redis


def add_user(user_id: str):
    r = redis.Redis(host='redishost')
    r.set(user_id, '1')


def user_exists(user_id: str) -> bool:
    r = redis.Redis(host='redishost')
    valid = r.get(user_id)
    if valid:
        # TODO delete print
        print(f"Found user {user_id} in cache!")
        return True
    else:
        return False
