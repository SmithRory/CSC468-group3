# import redis
# from datetime import timedelta


def add(stock_symbol, stock_price, quoteServerTime, redisHost):
#     r = redis.Redis(host='redishost')
    redisHost.set(stock_symbol, stock_price)
    redisHost.expire(stock_symbol, (int(quoteServerTime)+1000))

# param:
#       stock_symbol : String value of upto three letters For e.g., ABC
# returns:
#       stock_price : value of the stock
def get(stock_symbol, redishost):
#     r = redis.Redis(host='redishost')
    stock_price = redisHost.get(stock_symbol)
    if stock_price:
        stock_price = float(stock_price)
    return stock_price