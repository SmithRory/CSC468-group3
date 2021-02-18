import threading
import time
from database.accounts import Accounts, Stocks
from database.logs import DebugType
from legacy import quote
from mongoengine import DoesNotExist
import decimal

class UserPollingStocks:
    '''
    This class exists so the system can keep track of which stocks to poll, and which users have auto
    transactions for each of those stocks. This info will eventually be in a cache.
    '''

    def __init__(self):
        self._lock = threading.Lock()
        self.user_polling_stocks = {} 
        ''' user_polling_stocks format
        { 'stock_symbol' : { 
            'auto_buy': ['user1', 'user2'], 
            'auto_sell': ['user1', 'user2'], 
            'lastTransNum': 4, 
            'lastCommand': SET_BUY_TRIGGER, 
            'lastUser': 'user1'} }
        '''

    def get_stocks(self):
        return self.user_polling_stocks.keys()

    def get_last_info(self, stock_symbol):
        '''
        Returns a list containing:
            last transaction number [0],
            last command [1],
            last userid [2]
        '''
        transNum = self.user_polling_stocks[stock_symbol]['lastTransNum']
        command = self.user_polling_stocks[stock_symbol]['lastCommand']
        user = self.user_polling_stocks[stock_symbol]['lastUser']
        return list((transNum, command, user))

    def remove_user_autobuy(self, user_id, stock_symbol):
        with self._lock:
            try:
                self.user_polling_stocks[stock_symbol]['auto_buy'].remove(user_id)
            except KeyError:
                # User wasn't in list. Nothing to be done.
                pass

    def add_user_autobuy(self, user_id, stock_symbol, transactionNum, command):
        with self._lock:
            auto_transactions = self.user_polling_stocks.setdefault(stock_symbol, {'auto_buy': [], 'auto_sell': []})
            if user_id not in auto_transactions['auto_buy']:
                auto_transactions['auto_buy'].append(user_id)
                auto_transactions['lastTransNum'] = transactionNum
                auto_transactoins['lastCommand'] = command
                auto_transactions['lastUser'] = user_id

    def remove_user_autosell(self, user_id, stock_symbol):
        with self._lock:
            try:
                self.user_polling_stocks[stock_symbol]['auto_sell'].remove(user_id)
            except KeyError:
                # User wasn't in list. Nothing to be done.
                pass

    def add_user_autosell(self, user_id, stock_symbol, transactionNum, command):
        with self._lock:
            auto_transactions = self.user_polling_stocks.setdefault(stock_symbol, {'auto_buy': [], 'auto_sell': []})
            if user_id not in auto_transactions['auto_sell']:
                auto_transactions['auto_sell'].append(user_id)
                auto_transactions['lastTransNum'] = transactionNum
                auto_transactoins['lastCommand'] = command
                auto_transactions['lastUser'] = user_id

class QuotePollingThread(threading.Thread):
    '''
    Polls the stocks prices and triggers any auto sell/buy transactions when necessary.
    '''

    def __init__(self, quote_polling, polling_rate):
        threading.Thread.__init__(self)
        self.quote_polling = quote_polling
        self.polling_rate = polling_rate

    def run(self):
        while True:
            # Get all the stocks that have auto buy/sells.
            stocks = self.quote_polling.get_stocks()

            # For each stock call the quote update handler.
            if len(stocks) != 0:
                for stock in stocks:
                    self.quote_update_handler(stock)

            # Sleep for the polling rate.
            time.sleep(self.polling_rate)

    def quote_update_handler(self, stock_symbol):
        # Get the most up-to-date command information for logging purposes.
        info = self.quote_polling.get_last_info(stock_symbol)

        value = quote.get_quote(uid=info[2], stock_name=stock_symbol, transactionNum=info[0], userCommand=info[1])

        # Get all users that have an auto buy trigger equal to or less than the quote value.
        auto_buy_users = Accounts.objects(__raw__={"auto_buy": {"$elemMatch": {"symbol": stock_symbol, "trigger": {"$lte": value}}}}).only('user_id')

        # Perform auto buy for all the users.
        for user_id in auto_buy_users:
            self.auto_buy_handler(user_id, stock_symbol, value)
            
            # Remove user from list of auto_buys
            self.quote_polling.remove_user_autobuy(user_id = user_id, stock_symbol = stock_symbol)

        # Get all users that have an auto sell trigger equal to or greater than the quote value.
        auto_sell_users = Accounts.objects(__raw__={"auto_sell": {"$elemMatch": {"symbol": stock_symbol, "trigger": {"$gte": value}}}}).only('user_id')
        
        # Perform auto sell for all the users.
        for user_id in auto_sell_users:
            self.auto_sell_handler(user_id, stock_symbol, value)
            
            # Remove user from list of auto_sells
            self.quote_polling.remove_user_autosell(user_id = user_id, stock_symbol = stock_symbol)

    # Called whenever a user has an auto buy that gets triggered.
    def auto_buy_handler(self, user_id, stock_symbol, value):
        print(f"Autobuy triggered for {user_id} since stock {stock_symbol} reached {value}.")

        # Get the user document
        user_account = Accounts.objects.get(user_id=user_id)

        # Remove the auto buy transaction from the users list of auto buys
        users_auto_buy = user_account.auto_buy.get(stock_symbol=stock_symbol)
        user_account.auto_buy.remove(users_auto_buy)

        # Add the difference between the reserved amount and transaction cost to the amount available.
        # Deduct the transaction cost from the account.
        reserved_amount = users_auto_buy.amount * users_auto_buy.trigger
        transaction_cost = users_auto_buy.amount * value
        user_account.available = user_account.available + decimal.Decimal(reserved_amount - transaction_cost)
        user_account.amount = user_account.amount - decimal.Decimal(transaction_cost)
        
        # Update the number of stocks owned.
        users_stocks = None
        try:
            users_stock = user_account.stocks.get(symbol=stock_symbol)
        except DoesNotExist:
            # Create a new stock
            new_stock = Stocks(symbol=stock_symbol, amount=users_auto_buy.amount, available=users_auto_buy.amount)      
            user_account.stocks.append(new_stock)
        else:
            # Increment the amount of stock
            users_stock.amount = users_stock.amount + users_auto_buy.amount
            users_stock.available = users_stock.available + users_auto_buy.amount

        # Save the user.
        user_account.save()

        # Notify the user.
        print(f"Successfully completed auto buy of {users_auto_buy.amount} shares of stock {stock_symbol}.")

    # Called whenever a user has an auto sell that gets triggered.
    def auto_sell_handler(self, user_id, stock_symbol, value):
        print(f"Autosell triggered for {user_id} since stock {stock_symbol} reached {value}.")

        # Get the user document
        users_account = Accounts.objects.get(user_id=user_id)

        # Remove the auto sell.
        users_auto_sell = users_account.auto_sell.get(symbol=stock_symbol)
        users_account.auto_sell.remove(users_auto_sell)

        # Decrease the number of owned stocks.
        users_stock = users_account.stocks.get(symbol=stock_symbol)
        users_stock.amount = users_stock.amount - users_auto_sell.amount 
        if users_stock.amount == 0:
            users_account.stocks.remove(users_stock) 

        # Adjust the funds in the account.
        users_account.account = users_account.account + decimal.Decimal(value * users_auto_sell.amount)

        # Save the user.
        users_account.save()

        # Notify the user.
        print(f"Successfully completed auto sell of {users_auto_sell.amount} shares of stock {stock_symbol}.")