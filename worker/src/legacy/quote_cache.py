import redis
from datetime import timedelta

# from dataclasses import dataclass
# import time

''' This is a temporary replacement for Reddis cache
for use in the 1 user workload test only. Going forward
Reddis will be implemented and replace this file.
'''

# @dataclass
# class Quote:
#     stock_name: str
#     value: float
#     timestamp: float
#
# cache = {} # {stock_name: Quote}
# UPDATE_FREQ = 4 # Values are outdated after 4 seconds


def add(stock_symbol, stock_price, quoteServerTime):
    r = redis.Redis(host='redishost')
    r.set(stock_symbol, stock_price)
    r.expire(stock_symbol, (quoteServerTime+1000))

# param:
#       stock_symbol : String value of upto three letters For e.g., ABC
# returns:
#       stock_price : value of the stock
def get(stock_symbol):
    r = redis.Redis(host='redishost')
    stock_price = r.get(stock_symbol)
    if stock_price:
        stock_price = float(stock_price)
    return stock_price