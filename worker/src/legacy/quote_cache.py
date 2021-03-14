import redis
from datetime import timedelta

def add(stock_symbol, stock_price, quoteServerTime):
    r = redis.Redis(host='redishost')
    r.set(stock_symbol, stock_price)
    r.expire(stock_symbol, (int(quoteServerTime)+1000))

def get(stock_symbol):
    r = redis.Redis(host='redishost')
    stock_price = r.get(stock_symbol)
    if stock_price:
        stock_price = float(stock_price)
    return stock_price