from database.accounts import Accounts, Stocks, AutoTransaction, get_users
from mongoengine import DoesNotExist
from threading import Timer
from math import floor
from legacy import quote, quote_cache
import decimal

# TODO: perform atomic updates instead of querying document, modifying it, and then saving it
# Helpful Doc https://docs.mongoengine.org/guide/querying.html#atomic-updates

# TODO: split this up more nicely

# TODO: logging

class CMDHandler:

    def __init__(self):
        self.uncommitted_buys = {} # which users have a pending buy, and the transaction info
        self.uncommitted_buy_timers = {} # the timer for each pending buy
        self.uncommitted_sells = {}
        self.uncommitted_sell_timers = {}
    
    # params: user_id, amount
    def add(self, params):
        amount = params[1]
        user_id = params[0]

        # Get the user
        # Note: user.account will return a 'float' if the user
        # has not been created, and 'decimal.Decimal` if they have been.
        try:
            user = Accounts.objects.get(user_id=user_id)
        except DoesNotExist:
            # Create the user if they don't exist
            # Add into the accounts
            user = Accounts(user_id=user_id)
            user.account = user.account + amount
            user.available = user.available + amount
        else:
            # Update the account.
            user.account = user.account + decimal.Decimal(amount)
            user.available = user.available + decimal.Decimal(amount)

        # Save the user
        try:
            user.save()
        except Exception as e:
            # Let user know of the error
            print(e)

        # Notify the user
        print(f"Successfully added ${amount} to account.")
        

    # params: user_id, stock_symbol
    def quote(self, params):
        print("QUOTE: ", params)

        user_id = params[0]
        stock_symbol = params[1]

        # Get the quote from the stock server
        value = quote.get_quote(user_id, stock_symbol)

        # Forward the quote to the frontend so the user can see it
        print(f"{stock_symbol} has value {value}")
        

    # params: user_id, stock_symbol, amount
    def buy(self, params):
        print("BUY: ", params)

        user_id = params[0]
        stock_symbol = params[1]
        max_debt = float(params[2]) # Maximum dollar amount of the transaction

        # Get a quote for the stock the user wants to buy
        value = quote.get_quote(user_id, stock_symbol)

        # Find the number of stocks the user can buy
        num_stocks = floor(max_debt/value) # Ex. max_dept=$100,value=$15per/stock-> num_stocks=6
        if num_stocks==0:
            # Notify the user the stock costs more than the amount given.
            print(f"The price of stock {stock_symbol} ({value}) is more than the amount requested ({max_debt}).")
            return
        
        # Check if the user has enough available
        trans_price = value*num_stocks
        funds_available = Accounts.objects.get(user_id=user_id).available
        if trans_price > funds_available:
            # Notify the user they don't have enough available funds.
            print("Insufficent funds to purchase stock.")
            return

        # Forward the user the quote, prompt user to commit or cancel the buy command.
        print(f'Purchace price ({stock_symbol}): ${value} per stock x {num_stocks} stocks = ${trans_price}\nPlease issue COMMIT_BUY or CANCEL_BUY to complete the transaction.')
        
        # Add the uncommitted buy to the list.
        uncommitted_buy = {user_id: {'stock': stock_symbol, 'num_stocks': num_stocks, 'quote': value, 'amount': max_debt}}
        self.uncommitted_buys.update(uncommitted_buy)
        
        # Cancel any previous timers for this user. There can only be one pending buy at a time.
        previous_timer = self.uncommitted_buy_timers.pop(user_id, None)
        if previous_timer is not None:
            previous_timer.cancel()

        # Created a new timer to timeout when a COMMIT or CANCEL has not been issued.
        commit_timer = Timer(60.0, self.buy_timeout_handler, [user_id]) # 60 seconds
        commit_timer.start()
        self.uncommitted_buy_timers.update({user_id: commit_timer})        

    # Gets called when a BUY command has timed out (no COMMIT or CANCEL).
    def buy_timeout_handler(self, user_id):

        # Remove the timer
        timer = self.uncommitted_buy_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()
        
        # Remove the pending buy
        users_buy = self.uncommitted_buys.pop(user_id, None)

        # Notify the user their BUY has expired.
        print("The BUY command has expired and will be re-issued.")

        # Re-issue the buy command.
        self.buy([user_id, users_buy['stock'], users_buy['amount']])

    # params: user_id
    def commit_buy(self, params):
        print("COMMIT_BUY: ", params)
        
        user_id = params[0]

        # Check to see if the user has issued a buy command.
        users_buy = self.uncommitted_buys.pop(user_id, None)
        if users_buy is None:
            # Must issue a BUY command first
            print("Invalid command. A BUY command has not been issued.")
            return

        # Cancel the commit timer
        commit_timer = self.uncommitted_buy_timers.pop(user_id, None)
        if commit_timer is not None:
            commit_timer.cancel()

        # Complete the transaction.
        # Deduct the cost of the purchase.
        user_account = Accounts.objects.get(user_id=user_id)
        cost = decimal.Decimal(users_buy['num_stocks'] * users_buy['quote'])
        user_account.account = user_account.account - cost
        user_account.available = user_account.available - cost
        
        # Check if they already have some of this stock
        users_stocks = None
        try:
            users_stock = user_account.stocks.get(symbol=users_buy['stock'])
        except DoesNotExist:
            # Create a new stock
            new_stock = Stocks(symbol=users_buy['stock'], amount=users_buy['num_stocks'])      
            user_account.stocks.append(new_stock)
        else:
            # Increment the amount of stock
            users_stock.amount = users_stock.amount + users_buy['num_stocks']

        # Save the document.
        user_account.save()

        # Notify the user.
        print("Successfully purchased stock.")

    # params: user_id
    def cancel_buy(self, params):
        print("CANCEL_BUY: ", params)
        
        user_id = params[0]

        #Check to see if the user has issued a buy command.
        users_buy = self.uncommitted_buys.pop(user_id, None)
        if users_buy is None:
            # Must issue a BUY command first
            print("Invalid command. A BUY command has not been issued.")
            return

        # Cancel the commit timer
        commit_timer = self.uncommitted_buy_timers.pop(user_id, None)
        if commit_timer is not None:
            commit_timer.cancel()

        # Notify the user.
        print("Successfully cancelled stock purchase.")

    # params: user_id, stock_symbol, amount
    def sell(self, params):
        print("SELL: ", params)

        user_id = params[0]
        stock_symbol = params[1]
        sell_amount = params[2] # dollar amount of the stock to sell

        # Get a quote for the stock the user wants to buy
        value = quote.get_quote(user_id, stock_symbol)

        # Find the number of stocks the user owns.
        user_account = Accounts.objects.get(user_id=user_id)
        users_stock = None
        try:
            users_stock = user_account.stocks.get(symbol=stock_symbol)
        except DoesNotExist:
            # The user does not own any of the stock they want to sell.
            print(f"Invalid SELL command. The stock {stock_symbol} is not owned.")
            return

        # Check if the user has enough of the given stock.
        num_to_sell = floor(sell_amount/value)
        if num_to_sell > users_stock.amount:
            # The user does not own enough of this stock
            print(f"Insufficent number of stocks owned. Stocks needed ({num_to_sell}), stocks owned ({users_stock.amount}).")
            return

        # Forward the user the transaction info, prompt user to commit or cancel the buy command.
        print(f'Selling price ({stock_symbol}): ${value} per stock x {num_to_sell} stocks = ${value*num_to_sell}\nPlease issue COMMIT_SELL or CANCEL_SELL to complete the transaction.')

        # Add the uncommitted sell to the list.
        uncommitted_sell = {user_id: {'stock': stock_symbol, 'num_stocks': num_to_sell, 'quote': value, 'amount': sell_amount}}
        self.uncommitted_sells.update(uncommitted_sell)

        # Cancel any previous timers for this user. There can only be one pending sell at a time.
        previous_timer = self.uncommitted_sell_timers.pop(user_id, None)
        if previous_timer is not None:
            previous_timer.cancel()

        # Created a new timer to timeout when a COMMIT or CANCEL has not been issued.
        commit_timer = Timer(60.0, self.sell_timeout_handler, [user_id]) # 60 seconds
        commit_timer.start()
        self.uncommitted_sell_timers.update({user_id: commit_timer})    

    # Gets called when a SELL command has timed out (no COMMIT or CANCEL).
    def sell_timeout_handler(self, user_id):

        # Remove the timer.
        timer = self.uncommitted_sell_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()

        # Remove the pending sell.
        users_sell = self.uncommitted_sells.pop(user_id, None)

        # Notify the user their SELL has expired.
        print("The SELL command has expired and will be re-issued.")

        # Re-issue the SELL command.
        self.sell([user_id, users_sell['stock'], users_sell['amount']])

    # params: user_id
    def commit_sell(self, params):
        print("COMMIT_SELL: ", params)

        user_id = params[0]

        # Check to see if the user has issued a sell command.
        users_sell = self.uncommitted_sells.pop(user_id, None)
        if users_sell is None:
            # Must issue a SELL command first.
            print("Invalid command. Must issue a SELL command first.")
            return
        
        # Cancel the commit timer.
        timer = self.uncommitted_sell_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()

        # Complete the transaction.
        users_account = Accounts.objects.get(user_id=user_id)
        profit = decimal.Decimal(users_sell['num_stocks'] * users_sell['quote'])

        users_stocks = None
        try:
            users_stock = users_account.stocks.get(symbol=users_sell['stock'])
        except DoesNotExist:
            # This should never happen.
            print("Error. Stocks not found in users account.")
            return
        
        if users_stock.amount == users_sell['num_stocks']:
            # Remove the stock from the list.
            users_account.stocks.remove(users_stock)
        else:
            # Deduct the amount of the stock.
            users_stock.amount = users_stock.amount - users_sell['num_stocks']

        # Add the transaction profit to the account.
        users_account.account = users_account.account + profit
        users_account.available = users_account.available + profit

        # Save the document.
        users_account.save()

        # Notify the users.
        print(f"Successfully sold ${profit} of stock {users_sell['stock']}.")

    # params: user_id
    def cancel_sell(self, params):
        print("CANCEL_SELL: ", params)

        user_id = params[0]

        # Check to see if the user has issued a SELL command.
        users_sell = self.uncommitted_sells.pop(user_id, None)
        if users_sell is None:
            # Must issue a SELL command.
            print("Invalid command. A SELL command has not been issued.")

        # Cancel the timer.
        timer = self.uncommitted_sell_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()
        else:
            return

        # Notify the user.
        print("Successfully cancelled sell transaction.")

    # params: user_id, stock_symbol, amount
    def set_buy_amount(self, params):
        print("SET_BUY_AMOUNT: ", params)

        # Check the user's account has enough money

        # Deduct money from the available account
        # Add the stock and amount to the user's auto_buy list

    # params: user_id, stock_symbol
    def cancel_set_buy(self, params):
        print("CANCEL_SET_BUY: ", params)

    # params: user_id, stock_symbol, amount
    def set_buy_trigger(self, params):
        print("SET_BUY_TRIGGER: ", params)

    # params: user_id, stock_symbol, amount
    def set_sell_amount(self, params):
        print("SET_SELL_AMOUNT: ", params)

    # params: user_id, stock_symbol, amount
    def set_sell_trigger(self, params):
        print("SET_SELL_TRIGGER: ", params)

    # params: user_id, stock_symbol
    def cancel_set_sell(self, params):
        print("CANCEL_SET_SELL: ", params)

    # params: user_id(optional), filename
    def dumplog(self, params):
        print("DUMPLOG: ", params)

    # params: user_id
    def display_summary(self, params):
        print("DISPLAY_SUMMARY: ", params)

    def unknown_cmd(self, params):
        print("UNKNOWN COMMAND!")

    def handle_command(self, cmd, params):
        
        switch = {
            "ADD": self.add,
            "QUOTE": self.quote,
            "BUY": self.buy,
            "COMMIT_BUY": self.commit_buy,
            "CANCEL_BUY": self.cancel_buy,
            "SELL": self.sell,
            "COMMIT_SELL": self.commit_sell,
            "CANCEL_SELL": self.cancel_sell,
            "SET_BUY_AMOUNT": self.set_buy_amount, 
            "CANCEL_SET_BUY": self.cancel_set_buy,
            "SET_BUY_TRIGGER": self.set_buy_trigger,
            "SET_SELL_AMOUNT": self.set_sell_amount,
            "SET_SELL_TRIGGER": self.set_sell_trigger,
            "CANCEL_SET_SELL": self.cancel_set_sell,
            "DUMPLOG": self.dumplog,
            "DISPLAY_SUMMARY": self.display_summary
        }
        
        # Get the function
        func = switch.get(cmd, self.unknown_cmd)
        # Call the function to handle the command
        func(params)