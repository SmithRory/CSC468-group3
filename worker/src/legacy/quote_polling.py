import threading

class UserPollingStocks:
    def __init__(self):
        self.lock = threading.Lock()
        self.user_polling_stocks = {} # { 'stock_symbol' : { 'auto_buy': ['user1', 'user2'], 'auto_sell': ['user1', 'user2'] } }

    def get_users_autobuy(self, stock_symbol):
        
    
    # add user to auto buys
    # remove user from auto buy list
    # get userids from auto buys

    # add user to auto sell
    # remove user from auto sell list
    # get usersids from autosells



# maybe make this a single function
class QuotePollingThread(threading.Thread):

    self.POLLING_RATE = 1

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
