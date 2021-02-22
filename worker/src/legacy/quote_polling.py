import threading
import time
from database.accounts import Accounts, Stocks
from database.logs import DebugType, AccountTransactionType
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
            'auto_buy': {'user1':2, 'user2':50}, # key is the user_id, value is the transactionNumber
            'auto_sell': {'user1':25, 'user2':59}, # key is the user_id, value is the transactionNumber
            'lastTransNum': 4, 
            'lastCommand': 'SET_BUY_TRIGGER', 
            'lastUser': 'user1'} }
        '''

    def get_stocks(self):
        ''' Returns a list of all keys. '''
        return list(self.user_polling_stocks)

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

    def remove_if_empty(self, stock_symbol):
        '''
        MUST have lock before calling this function.
        This should only ever be called from within this class.
        '''
        len_buy = len(self.user_polling_stocks[stock_symbol]['auto_buy'])
        len_sell = len(self.user_polling_stocks[stock_symbol]['auto_sell'])

        if len_buy == 0 and len_sell == 0:
            del self.user_polling_stocks[stock_symbol]

    def get_user_autobuy(self, user_id, stock_symbol):
        ''' Removes the user from the dictionary and returns the user's transaction number (None if does not exist). '''
        with self._lock:
            if stock_symbol in self.user_polling_stocks:
                user_transaction_num = self.user_polling_stocks[stock_symbol]['auto_buy'].pop(user_id, None)
                self.remove_if_empty(stock_symbol)
                return user_transaction_num
            else: return None

    def add_user_autobuy(self, user_id, stock_symbol, transactionNum, command):
        with self._lock:
            print(f"Adding stock {stock_symbol} to user_polling_stocks: {self.user_polling_stocks}")
            # Create dictionary for this stock if it's not made.
            auto_transactions = self.user_polling_stocks.setdefault(stock_symbol, {'auto_buy': {}, 'auto_sell': {}})
            print(f"After set default, user Polling stocks: {self.user_polling_stocks}\nauto_transactions: {auto_transactions}")
            # Set the values.
            auto_transactions['auto_buy'][user_id] = transactionNum
            auto_transactions['lastTransNum'] = transactionNum
            auto_transactions['lastCommand'] = command
            auto_transactions['lastUser'] = user_id
            print(f"After all, user Polling stocks: {self.user_polling_stocks}\nauto_transactions: {auto_transactions}")

    def get_user_autosell(self, user_id, stock_symbol):
        ''' Removes the user from the dictionary and returns the user's transaction number (None if does not exist). '''
        with self._lock:
            if stock_symbol in self.user_polling_stocks:
                user_transaction_num = self.user_polling_stocks[stock_symbol]['auto_sell'].pop(user_id, None)
                self.remove_if_empty(stock_symbol)
                return user_transaction_num
            else: return None

    def add_user_autosell(self, user_id, stock_symbol, transactionNum, command):
        with self._lock:
            # Create dictionary for this stock if it's not made.
            auto_transactions = self.user_polling_stocks.setdefault(stock_symbol, {'auto_buy': {}, 'auto_sell': {}})
            
            # Set the values.
            auto_transactions['auto_sell'][user_id] = transactionNum
            auto_transactions['lastTransNum'] = transactionNum
            auto_transactions['lastCommand'] = command
            auto_transactions['lastUser'] = user_id

class QuotePollingThread(threading.Thread):
    '''
    Polls the stocks prices and triggers any auto sell/buy transactions when necessary.
    '''

    def __init__(self, quote_polling, polling_rate, response_publisher):
        threading.Thread.__init__(self)
        self.quote_polling = quote_polling
        self.polling_rate = polling_rate
        self.response_publisher = response_publisher

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

        # Get the current stock price.
        value = quote.get_quote(uid=info[2], stock_name=stock_symbol, transactionNum=info[0], userCommand=info[1])

        # Get all users that have an auto buy trigger equal to or less than the quote value.
        auto_buy_users = Accounts.objects(__raw__={"auto_buy": {"$elemMatch": {"symbol": stock_symbol, "trigger": {"$lte": value}}}}).only('user_id')
        print(f"AUTO_BUY_USERS: {auto_buy_users.to_json()}")

        # Get all users that have an auto sell trigger equal to or greater than the quote value.
        auto_sell_users = Accounts.objects(__raw__={"auto_sell": {"$elemMatch": {"symbol": stock_symbol, "trigger": {"$gte": value}}}}).only('user_id')
        print(f"AUTO_BUY_USERS: {auto_buy_users.to_json()}")

        # Perform auto buy for all the users.
        for user in auto_buy_users:
            user_id = user.user_id
            transactionNum = self.quote_polling.get_user_autobuy(user_id = user_id, stock_symbol = stock_symbol)

            if transactionNum is None:
                # Error
                err_msg = f"Error: Failed to get transaction number for {user_id}. Cannot complete auto buy."
                print(err_msg)
                continue
            else:
                self.auto_buy_handler(user_id=user_id, stock_symbol=stock_symbol, value=value, transactionNum=transactionNum) 
        
        # Perform auto sell for all the users.
        for user in auto_sell_users:
            user_id = user.user_id
            transactionNum = self.quote_polling.get_user_autosell(user_id = user_id, stock_symbol = stock_symbol)
            
            if transactionNum is None:
                # Error
                err_msg = f"Error: Failed to get transaction number for {user_id}. Cannot complete auto sell."
                print(err_msg)
                continue
            else:
                self.auto_sell_handler(user_id=user_id, stock_symbol=stock_symbol, value=value, transactionNum=transactionNum)

    # Called whenever a user has an auto buy that gets triggered.
    def auto_buy_handler(self, user_id, stock_symbol, value, transactionNum):
        info_msg = f"[{transactionNum}] Autobuy triggered for {user_id} since stock {stock_symbol} reached ${value:.2f}."
        print(info_msg)
        DebugType().log(transactionNum=transactionNum, command="SET_BUY_TRIGGER", username=user_id, debugMessage=info_msg)

        # Get the user document
        user_account = Accounts.objects.get(pk=user_id)

        # Remove the auto buy transaction from the users list of auto buys
        users_auto_buy = user_account.auto_buy.get(symbol=stock_symbol)
        user_account.auto_buy.remove(users_auto_buy)

        # Add the difference between the reserved amount and transaction cost to the amount available.
        # Deduct the transaction cost from the account.
        reserved_amount = users_auto_buy.amount * users_auto_buy.trigger
        transaction_cost = users_auto_buy.amount * value
        user_account.available = user_account.available + decimal.Decimal(reserved_amount) - decimal.Decimal(transaction_cost)
        user_account.account = user_account.account - decimal.Decimal(transaction_cost)
        
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
        ok_msg = f"[{transactionNum}] Successfully completed auto buy of {users_auto_buy.amount} shares of stock {stock_symbol} for user {user_id}."
        print(ok_msg)
        self.response_publisher.send(ok_msg)
        AccountTransactionType().log(transactionNum=transactionNum, action="remove", username=user_id, funds=transaction_cost)

    # Called whenever a user has an auto sell that gets triggered.
    def auto_sell_handler(self, user_id, stock_symbol, value, transactionNum):
        info_msg = f"[{transactionNum}] Autosell triggered for {user_id} since stock {stock_symbol} reached ${value:.2f}."
        print(info_msg)
        DebugType().log(transactionNum=transactionNum, command="SET_SELL_TRIGGER", username=user_id, debugMessage=info_msg)

        # Get the user document
        users_account = Accounts.objects.get(pk=user_id)

        # Remove the auto sell.
        users_auto_sell = users_account.auto_sell.get(symbol=stock_symbol)
        users_account.auto_sell.remove(users_auto_sell)

        # Decrease the number of owned stocks.
        users_stock = users_account.stocks.get(symbol=stock_symbol)
        users_stock.amount = users_stock.amount - users_auto_sell.amount 
        if users_stock.amount == 0:
            users_account.stocks.remove(users_stock) 

        # Adjust the funds in the account.
        sale_profit = decimal.Decimal(value) * decimal.Decimal(users_auto_sell.amount)
        users_account.account = users_account.account + sale_profit
        users_account.available = users_account.available + sale_profit

        # Save the user.
        users_account.save()

        # Notify the user.
        ok_msg = f"[{transactionNum}] Successfully completed auto sell of {users_auto_sell.amount} shares of stock {stock_symbol} for user {user_id}."
        print(ok_msg)
        self.response_publisher.send(ok_msg)
        AccountTransactionType().log(transactionNum=transactionNum, action="add", username=user_id, funds=sale_profit)