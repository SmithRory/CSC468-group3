import redis
from datetime import timedelta


def add(stock_symbol, stock_price, quote_server_time, redis_cache):
    redis_cache.set(stock_symbol, stock_price)
    redis_cache.expire(stock_symbol, (int(quote_server_time)+1000))


def get(stock_symbol, redis_cache):
    stock_price = redis_cache.get(stock_symbol)
    if stock_price:
        stock_price = float(stock_price)
    return stock_price
