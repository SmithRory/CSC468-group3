# param:
#       stock_symbol : String value of upto three letters For e.g., ABC
#       stock_price : The value of the stock
#       quoteServerTime : The time when the stock_price was received, this is for calculating the expiry time
#       redisHost : The redis host the worker is connected to
# returns:
#       stock_price : value of the stock
#
def add(stock_symbol, stock_price, quoteServerTime, redisHost):
    redisHost.set(stock_symbol, stock_price)
    redisHost.expire(stock_symbol, (int(quoteServerTime)+1000))

# param:
#       stock_symbol : String value of upto three letters For e.g., ABC
#       redisHost : The redis host the worker is connected to
# returns:
#       stock_price : value of the stock
def get(stock_symbol, redisHost):
    stock_price = redisHost.get(stock_symbol)
    if stock_price:
        stock_price = float(stock_price)
    return stock_price