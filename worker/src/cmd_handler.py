from database.accounts import Accounts, Stocks, AutoTransaction, get_users
from database.logs import get_logs, AccountTransactionType, UserCommandType, SystemEventType, ErrorEventType
from mongoengine import DoesNotExist
from threading import Timer
from math import floor
from legacy import quote, quote_cache, quote_polling
from LogFile import log_handler

import decimal
import time

# TODO: perform atomic updates instead of querying document, modifying it, and then saving it
# Helpful Doc https://docs.mongoengine.org/guide/querying.html#atomic-updates

# TODO: extract repeated logic into their own function

# TODO: logging

# TODO: check the user exists before executing commands (this is only being done for the ADD so far)

# TODO: turn dictionaries into cache 

class CMDHandler:

    def __init__(self):
        # Auto-buy.
        self.uncommitted_buys = {} # which users have a pending buy, and the transaction info
        self.uncommitted_buy_timers = {} # the timer for each pending buy
        
        # Auto-sell.
        self.uncommitted_sells = {}
        self.uncommitted_sell_timers = {}
        self.pending_sell_triggers = {} # Holds pending auto sells until a sell trigger is given.

        # Quote polling for auto buy/sell.
        self.POLLING_RATE = 1
        self.quote_polling = quote_polling.UserPollingStocks()
        self.polling_thread = quote_polling.QuotePollingThread(quote_polling = self.quote_polling, polling_rate = self.POLLING_RATE)
        self.polling_thread.setDaemon(True) # will be cleaned up on exit
        self.polling_thread.start()

    # params: user_id, amount
    def add(self, transactionNum, params):
        amount = params[1]
        user_id = params[0]
        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "ADD", username=user_id, funds=amount)

        # Get the user
        # Note: user.account will return a 'float' if the user
        # has not been created, and 'decimal.Decimal` if they have been.
        try:
            user = Accounts.objects.get(user_id=user_id)
        except DoesNotExist:
            # Create the user if they don't exist.
            user = Accounts(user_id=user_id)
            user.account = user.account + amount
            user.available = user.available + amount

            # TODO
            # Log DebugType.log that a user has been added do the system.

        else:
            # Update the account.
            user.account = user.account + decimal.Decimal(amount)
            user.available = user.available + decimal.Decimal(amount)

        # Save the user
        try:
            user.save()
            AccountTransactionType().log((round(time.time()*1000)), "Worker", transactionNum, "add", user_id, amount)
        except Exception as e:
            # Let user know of the error
            print(e)

            ErrorEventType().log((round(time.time()*1000)), "Worker", transactionNum, "ADD", username=user_id, funds=amount, errorMessage="The user could not be saved")

            return

        # Notify the user
        print(f"Successfully added ${amount} to account.")

    # params: user_id, stock_symbol
    def quote(self, transactionNum, params):
        print("QUOTE: ", params)

        user_id = params[0]
        stock_symbol = params[1]

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "QUOTE", username=user_id, stockSymbol=stock_symbol)

        # Get the quote from the stock server
        value = quote.get_quote(user_id, stock_symbol, transactionNum, "QUOTE")

        # Forward the quote to the frontend so the user can see it
        print(f"{stock_symbol} has value {value}")

    # params: user_id, stock_symbol, amount
    def buy(self, transactionNum, params):
        print("BUY: ", params)

        user_id = params[0]
        stock_symbol = params[1]
        max_debt = float(params[2]) # Maximum dollar amount of the transaction

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "BUY", username=user_id, stockSymbol=stock_symbol, funds=max_debt)


        # Get a quote for the stock the user wants to buy
        value = quote.get_quote(user_id, stock_symbol, transactionNum, "BUY")

        # Find the number of stocks the user can buy
        num_stocks = floor(max_debt/value) # Ex. max_dept=$100,value=$15per/stock-> num_stocks=6
        if num_stocks==0:
            # Notify the user the stock costs more than the amount given.
            print(f"The price of stock {stock_symbol} ({value}) is more than the amount requested ({max_debt}).")

            ErrorEventType().log((round(time.time()*1000)), "Worker", transactionNum, "BUY", username=user_id, stockSymbol=stock_symbol, funds=max_debt, errorMessage="The price of stock is more than the requested amount")
            return
        
        # Check if the user has enough available
        trans_price = value*num_stocks
        users_account = Accounts.objects.get(user_id=user_id)
        if trans_price > users_account.available:
            # Notify the user they don't have enough available funds.
            print("Insufficent funds to purchase stock.")

            ErrorEventType().log((round(time.time()*1000)), "Worker", transactionNum, "BUY", username=user_id, stockSymbol=stock_symbol, funds=max_debt, errorMessage="Insufficient funds")

            return
        else:
            # Decrement the amount of available funds until a COMMIT or CANCEL happens.
            # This is essentially reserving the funds.
            users_account.available = users_account.available - decimal.Decimal(trans_price)

        users_account.save()

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
    def buy_timeout_handler(self, transactionNum, user_id):

        # Remove the timer
        timer = self.uncommitted_buy_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()
        
        # Remove the pending buy
        users_buy = self.uncommitted_buys.pop(user_id, None)

        # Notify the user their BUY has expired.
        print("The BUY command has expired and will be re-issued.")

        # Free the reserved funds.
        users_account = Accounts.objects.get(user_id=user_id)
        users_account.available = users_account.available + decimal.Decimal(users_buy['num_stocks'] * users_buy['quote'])
        users_account.save()

        # Re-issue the buy command.
        self.buy([user_id, users_buy['stock'], users_buy['amount']])

    # params: user_id
    def commit_buy(self, transactionNum, params):
        print("COMMIT_BUY: ", params)
        
        user_id = params[0]

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "COMMIT_BUY", username=user_id)

        # Check to see if the user has issued a buy command.
        users_buy = self.uncommitted_buys.pop(user_id, None)
        if users_buy is None:
            # Must issue a BUY command first
            print("Invalid command. A BUY command has not been issued.")

            ErrorEventType().log((round(time.time()*1000)), "Worker", transactionNum, "COMMIT_BUY", username=user_id, errorMessage="Invalid command, a buy command has not been issued.")

            return

        # Cancel the commit timer
        commit_timer = self.uncommitted_buy_timers.pop(user_id, None)
        if commit_timer is not None:
            commit_timer.cancel()

        # Complete the transaction.
        # Deduct the cost of the purchase. Note: the amount has already been deducted from the available funds.
        user_account = Accounts.objects.get(user_id=user_id)
        cost = decimal.Decimal(users_buy['num_stocks'] * users_buy['quote'])
        user_account.account = user_account.account - cost
        
        # Check if they already have some of this stock
        users_stocks = None
        try:
            users_stock = user_account.stocks.get(symbol=users_buy['stock'])
        except DoesNotExist:
            # Create a new stock
            new_stock = Stocks(symbol=users_buy['stock'], amount=users_buy['num_stocks'], available=users_buy['num_stocks'])      
            user_account.stocks.append(new_stock)
        else:
            # Increment the amount of stock
            users_stock.amount = users_stock.amount + users_buy['num_stocks']
            users_stock.available = users_stock.available + users_buy['num_stocks']

        # Save the document.
        user_account.save()
        AccountTransactionType().log((round(time.time()*1000)), "Worker", transactionNum, "remove", user_id, cost)


        # Notify the user.
        print("Successfully purchased stock.")

    # params: user_id
    def cancel_buy(self, transactionNum, params):
        print("CANCEL_BUY: ", params)
        
        user_id = params[0]

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "CANCEL_BUY", username=user_id)

        # Cancel the commit timer
        commit_timer = self.uncommitted_buy_timers.pop(user_id, None)
        if commit_timer is not None:
            commit_timer.cancel()
            
        #Check to see if the user has issued a buy command.
        users_buy = self.uncommitted_buys.pop(user_id, None)
        if users_buy is None:
            # Must issue a BUY command first
            print("Invalid command. A BUY command has not been issued.")

            ErrorEventType().log((round(time.time()*1000)), "Worker", transactionNum, "CANCEL_BUY", username=user_id, errorMessage="Invalid command, a BUY command has not been issued yet")

            return

        # Free the reserved funds.
        users_account = Accounts.objects.get(user_id=user_id)
        users_account.available = users_account.available + decimal.Decimal(users_buy['num_stocks'] * users_buy['quote'])
        users_account.save()

        # Notify the user.
        print("Successfully cancelled stock purchase.")

    # params: user_id, stock_symbol, amount
    def sell(self, transactionNum, params):
        print("SELL: ", params)

        user_id = params[0]
        stock_symbol = params[1]
        sell_amount = params[2] # dollar amount of the stock to sell

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "SELL", username=user_id, stockSymbol=stock_symbol, funds=sell_amount)

        # Get a quote for the stock the user wants to sell
        value = quote.get_quote(user_id, stock_symbol, transactionNum, "SELL")

        # Find the number of stocks the user owns.
        users_account = Accounts.objects.get(user_id=user_id)
        users_stock = None
        try:
            users_stock = users_account.stocks.get(symbol=stock_symbol)
        except DoesNotExist:
            # The user does not own any of the stock they want to sell.
            print(f"Invalid SELL command. The stock {stock_symbol} is not owned.")

            ErrorEventType().log((round(time.time()*1000)), "Worker", transactionNum, "SELL", username=user_id, stockSymbol=stock_symbol, funds=sell_amount, errorMessage="Invalid command, stock is not owned")

            return

        # Check if the user has enough of the given stock.
        num_to_sell = floor(sell_amount/value)
        if num_to_sell > users_stock.available:
            # The user does not own enough of this stock
            print(f"Insufficient number of stocks owned. Stocks needed ({num_to_sell}), stocks available ({users_stock.available}).")

            ErrorEventType().log((round(time.time()*1000)), "Worker", transactionNum, "SELL", username=user_id, stockSymbol=stock_symbol, funds=sell_amount, errorMessage="Insufficient number of stocks owned")

            return

        # Forward the user the transaction info, prompt user to commit or cancel the buy command.
        print(f'Selling price ({stock_symbol}): ${value} per stock x {num_to_sell} stocks = ${value*num_to_sell}\nPlease issue COMMIT_SELL or CANCEL_SELL to complete the transaction.')

        # Add the uncommitted sell to the list.
        uncommitted_sell = {user_id: {'stock': stock_symbol, 'num_stocks': num_to_sell, 'quote': value, 'amount': sell_amount}}
        self.uncommitted_sells.update(uncommitted_sell)

        # Set aside the needed number of stocks.
        users_stock.available = users_stock.available - decimal.Decimal(num_to_sell)
        users_account.save()

        # Cancel any previous timers for this user. There can only be one pending sell at a time.
        previous_timer = self.uncommitted_sell_timers.pop(user_id, None)
        if previous_timer is not None:
            previous_timer.cancel()

        # Created a new timer to timeout when a COMMIT or CANCEL has not been issued.
        commit_timer = Timer(60.0, self.sell_timeout_handler, [user_id]) # 60 seconds
        commit_timer.start()
        self.uncommitted_sell_timers.update({user_id: commit_timer})    

    # Gets called when a SELL command has timed out (no COMMIT or CANCEL).
    def sell_timeout_handler(self, transactionNum, user_id):

        # Remove the timer.
        timer = self.uncommitted_sell_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()

        # Remove the pending sell.
        users_sell = self.uncommitted_sells.pop(user_id, None)

        # Free the reserved stocks.
        users_account = Accounts.objects.get(user_id=user_id)
        users_stock = users_account.stocks.get(symbol=users_sell['stock_symbol'])
        users_stock.available = users_stock.available + decimal.Decimal(users_sell['num_stocks'])
        users_account.save()

        # Notify the user their SELL has expired.
        print("The SELL command has expired and will be re-issued.")

        # Re-issue the SELL command.
        self.sell([user_id, users_sell['stock'], users_sell['amount']])

    # params: user_id
    def commit_sell(self, transactionNum, params):
        print("COMMIT_SELL: ", params)

        user_id = params[0]

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "COMMIT_SELL", username=user_id)

        # Check to see if the user has issued a sell command.
        users_sell = self.uncommitted_sells.pop(user_id, None)
        if users_sell is None:
            # Must issue a SELL command first.
            print("Invalid command. Must issue a SELL command first.")

            # TODO
            # log ErrorEventType.log

            return
        
        # Cancel the commit timer.
        timer = self.uncommitted_sell_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()

        # Complete the transaction.
        users_account = Accounts.objects.get(user_id=user_id)
        profit = decimal.Decimal(users_sell['num_stocks'] * users_sell['quote'])

        users_stock = None
        try:
            users_stock = users_account.stocks.get(symbol=users_sell['stock'])
        except DoesNotExist:
            # This should never happen.
            print(f"Error. Stock {users_sell['stock']} not found in users account.")

            # TODO
            # log ErrorEventType.log

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
        AccountTransactionType().log((round(time.time()*1000)), "Worker", transactionNum, "add", user_id, profit)

        # Notify the users.
        print(f"Successfully sold ${profit} of stock {users_sell['stock']}.")

    # params: user_id
    def cancel_sell(self, transactionNum, params):
        print("CANCEL_SELL: ", params)

        user_id = params[0]

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "CANCEL_SELL", username=user_id)

        # Cancel the timer.
        timer = self.uncommitted_sell_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()

        # Check to see if the user has issued a SELL command.
        users_sell = self.uncommitted_sells.pop(user_id, None)
        if users_sell is None:
            # Must issue a SELL command.
            print("Invalid command. A SELL command has not been issued.")

            # TODO
            # log ErrorEventType.log

            return

        # Free the reserved stocks.
        users_account = Accounts.objects.get(user_id=user_id)
        users_stock = users_account.stocks.get(symbol=users_sell['stock'])
        users_stock.available = users_stock.available + decimal.Decimal(users_sell['num_stocks'])
        users_account.save()

        # Notify the user.
        print("Successfully cancelled sell transaction.")

    # params: user_id, stock_symbol, amount
    def set_buy_amount(self, transactionNum, params):
        print("SET_BUY_AMOUNT: ", params)

        user_id = params[0]
        stock_symbol = params[1]
        buy_amount = round(params[2]) # Can only buy a whole number of shares.

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "SET_BUY_AMOUNT", username=user_id, stockSymbol=stock_symbol, funds=buy_amount)

        # Add the stock and amount to the user's auto_buy list

        users_account = Accounts.objects.get(user_id=user_id)
        users_auto_buy = None
        try:
            # Check if an auto buy already exists for this stock
            users_auto_buy = users_account.auto_buy.get(symbol=stock_symbol)
        except DoesNotExist:
            # Create the auto_buy embedded document for this stock.
            new_auto_buy = AutoTransaction(user_id=user_id, symbol=stock_symbol, amount=buy_amount)
            users_account.auto_buy.append(new_auto_buy)
        else:
            # Update the auto buy amount, reset the buy trigger.
            users_auto_buy.amount = buy_amount
            users_auto_buy.trigger = 0.00

        # Save the document.
        users_account.save()

        # Notify the user.
        print(f"Successful set to buy {buy_amount} stocks of {stock_symbol} automatically. Please issue SET_BUY_TRIGGER to set the trigger price.")

    # params: user_id, stock_symbol, amount
    def set_buy_trigger(self, transactionNum, params):
        print("SET_BUY_TRIGGER: ", params)

        user_id = params[0]
        stock_symbol = params[1]
        buy_trigger = params[2]

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "SET_BUY_TRIGGER", username=user_id, stockSymbol=stock_symbol, funds=buy_trigger)

        # Check the user has issued a SET_BUY_AMOUNT for the given stock.
        users_account = Accounts.objects.get(user_id=user_id)
        users_auto_buy = None
        try:
            users_auto_buy = users_account.auto_buy.get(symbol=stock_symbol)
        except DoesNotExist:
            # No SET_BUY_AMOUNT issued.
            print(f"Invalid command. A SET_BUY_AMOUNT must be issued for stock {stock_symbol} before a trigger can be set.")
            
            # TODO
            # log ErrorEventType.log
            
            return

        # Check the user's account has enough money available.
        transaction_price = round(buy_trigger * users_auto_buy.amount, 2)
        if transaction_price > users_account.available:
            # Insufficent funds.
            print(f"Invalid buy trigger. Insufficent funds for an auto buy. Funds available (${users_account.available}), auto buy cost (${transaction_price}).")
            
            # TODO
            # log ErrorEventType.log
            
            return

        # Set the auto buy trigger.
        users_auto_buy.trigger = buy_trigger

        # Deduct money from the available account
        users_account.available = users_account.available - decimal.Decimal(transaction_price)

        users_account.save()

        # Notify user.
        print(f"Successfully set an auto buy for {users_auto_buy.amount} stocks of {stock_symbol} at ${buy_trigger} per stock.")

        # Add the user to the list of auto_buys for the stock
        self.polling_stocks.add_user_autobuy(user_id, stock_symbol)
        #auto_transactions = self.user_polling_stocks.setdefault(stock_symbol, {'auto_buy': [], 'auto_sell': []})
        #if user_id not in auto_transactions['auto_buy']:
        #   auto_transactions['auto_buy'].append(user_id)

    # params: user_id, stock_symbol
    def cancel_set_buy(self, transactionNum, params):
        print("CANCEL_SET_BUY: ", params)

        user_id = params[0]
        stock_symbol = params[1]

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "CANCEL_SET_BUY", username=user_id, stockSymbol=stock_symbol)

        # Check to see if the user has an auto buy for this stock.
        users_account = Accounts.objects.get(user_id=user_id)
        users_auto_buy = None
        try:
            users_auto_buy = users_account.auto_buy.get(symbol=stock_symbol)
        except DoesNotExist:
            # User hasn't set up and auto buy.
            print(f"Invalid command. No auto buy setup for stock {stock_symbol}.")

            # TODO
            # log ErrorEventType.log

            return

        # Remove the auto buy. Add the reserved funds.
        users_account.auto_buy.remove(users_auto_buy)
        users_account.available = users_account.available + decimal.Decimal(users_auto_buy.amount * users_auto_buy.trigger)
        users_account.save()

        # Remove the user from the stock polling
        self.quote_polling.remove_user_autobuy(user_id = user_id, stock_symbol = stock_symbol)
        #auto_transactions = self.user_polling_stocks.get(stock_symbol, None)
        #if auto_transactions is not None:
        #    try:
        #        auto_transactions['auto_buy'].remove(user_id)
        #    except ValueError:
        #        # User wasn't in list. Shouldn't happen but non-fatal if it does.
        #        pass

        # Notify user.
        print(f"Successfully cancelled the auto buy for stock {stock_symbol}.")

    # params: user_id, stock_symbol, amount
    def set_sell_amount(self, transactionNum, params):
        print("SET_SELL_AMOUNT: ", params)

        user_id = params[0]
        stock_symbol = params[1]
        sell_amount = floor(params[2]) # Can only sell a whole number of shares.

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "SET_SELL_AMOUNT", username=user_id, stockSymbol=stock_symbol, funds=sell_amount)

        users_account = Accounts.objects.get(user_id=user_id)

        # Verify the user owns enough shares of the given stock.
        users_stock = None
        try:
            users_stock = users_account.stocks.get(symbol=stock_symbol)
        except DoesNotExist:
            # The user does not own any of the stock they want to sell.
            print(f"Invalid command. The stock {stock_symbol} is not owned.")

            # TODO
            # log ErrorEventType.log

            return

        if users_stock.available < sell_amount:
            print(f"Invalid command. Number of available stocks for {stock_symbol} is ({users_stock.available}) and is less than the amount set to sell {sell_amount}.")
            
            # TODO
            # log ErrorEventType.log
            
            return

        # Decrement the number of available shares.
        users_stock.available = users_stock.available - decimal.Decimal(sell_amount)
        users_account.save()

        # Add the auto sell to the dictionary until the SET_SELL_TRIGGER is received.
        pending_auto_sell = {(user_id,stock_symbol): {'sell_amount': sell_amount}}
        self.pending_sell_triggers.update(pending_auto_sell)

        # Notify the user.
        print(f"Successfully set to sell {sell_amount} stocks of {stock_symbol} automatically. Please issue SET_SELL_TRIGGER to set the trigger price.")

    # params: user_id, stock_symbol, amount
    def set_sell_trigger(self, transactionNum, params):
        print("SET_SELL_TRIGGER: ", params)

        user_id = params[0]
        stock_symbol = params[1]
        sell_trigger = params[2]

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "SET_SELL_TRIGGER", username=user_id, stockSymbol=stock_symbol, funds=sell_trigger)

        # Check the user has issused a SET_SELL_AMOUNT
        pending_auto_sell = self.pending_sell_triggers.pop((user_id,stock_symbol), None)
        if pending_auto_sell is None:
            print("Invalid command. Issue a SET_SELL_AMOUNT for this stock before setting the trigger price.")
            
            # TODO
            # log ErrorEventType.log
            
            return

        # Create the auto_sell
        users_account = Accounts.objects.get(user_id=user_id)
        users_auto_sell = None
        try:
            # Check to see if one exists for this stock
            users_auto_sell = users_account.auto_sell.get(symbol=stock_symbol)
        except DoesNotExist:
            # Create a new auto sell.
            new_auto_sell = AutoTransaction(user_id=user_id, symbol=stock_symbol, amount=pending_auto_sell['sell_amount'], trigger=sell_trigger)
            users_account.auto_sell.append(new_auto_sell)
        else:
            # Auto sell has already been setup for this stock.
            # Update the auto sell and adjust the amount of reserved stocks
            prev_stock_amount = users_auto_sell.amount

            users_auto_sell.amount = pending_auto_sell['sell_amount']
            users_auto_sell.trigger = sell_trigger

            users_stocks = users_account.stocks.get(symbol=stock_symbol)
            users_stocks.available = users_stocks.available + prev_stock_amount - users_auto_sell.amount

        users_account.save()

        # Notify the user
        print(f"Successfully set an auto sell for {pending_auto_sell['sell_amount']} stocks of {stock_symbol} when the price is at least ${sell_trigger} per stock.")
        
        # Add user to the list of auto_sells for the stock
        self.quote_polling.add_user_autosell(user_id = user_id, stock_symbol = stock_symbol)
        #auto_transactions = self.user_polling_stocks.setdefault(stock_symbol, {'auto_buy': [], 'auto_sell': []})
        #if user_id not in auto_transactions['auto_sell']:
        #    auto_transactions['auto_sell'].append(user_id)

    # params: user_id, stock_symbol
    def cancel_set_sell(self, transactionNum, params):
        print("CANCEL_SET_SELL: ", params)

        user_id = params[0]
        stock_symbol = params[1]

        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "CANCEL_SET_SELL", username=user_id, stockSymbol=stock_symbol)


        bad_cmd = True
        reserved_amount = 0
        users_account = Accounts.objects.get(user_id=user_id)

        # Check if just a SET_SELL_AMOUNT has been issued.
        pending_auto_sell = self.pending_sell_triggers.pop((user_id,stock_symbol), None)
        if pending_auto_sell is not None:
            reserved_amount = pending_auto_sell['sell_amount']
            bad_cmd = False

        if bad_cmd == True:
            # Check if a SET_SELL_AMOUNT and SET_SELL_TRIGGER has been issued.
            users_auto_sell = None
            try:
                users_auto_sell = users_account.auto_sell.get(symbol=stock_symbol)
                bad_cmd = False
            except:
                # No auto sell.
                pass

            # Remove the auto sell.
            users_account.auto_sell.remove(users_auto_sell)
            reserved_amount = users_auto_sell.amount
        
        if bad_cmd == True:
            # No SET_SELL commands have been issued.
            print(f"Invalid command. No auto sell has been setup for stock {stock_symbol}.")

#             ErrorEventType().log((round(time.time()*1000)), "Worker", transactionNum, "CANCEL_SET_SELL", username=user_id, stockSymbol=stock_symbol, errorMessage="Invalid command, no auto sell has been set up")

            return

        # Release the reserved stocks.
        users_stocks = users_account.stocks.get(symbol=stock_symbol)
        users_stocks.available = users_stocks.available + reserved_amount
        users_account.save()

        # Remove the user from the auto_sell list
        self.quote_polling.remove_user_autosell(user_id = user_id, stock_symbol = stock_symbol)
        #auto_transactions = self.user_polling_stocks.get(stock_symbol, None)
        #if auto_transactions is not None:
        #    try:
        #        auto_transactions['auto_sell'].remove(user_id)
        #    except ValueError:
        #        # User wasn't in list. Shouldn't happen but non-fatal if it does.
        #        pass

        # Notify user.
        print(f"Successfully cancelled automatic selling of stock {stock_symbol}.")

    # params: filename, user_id(optional)
    def dumplog(self, transactionNum, params):

        # use user_id here to get data from databaseCA
        filename = params[0]
        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "DUMPLOG", filename=filename)

        json_data = get_logs() #this will be logs we get from the database
        log_handler.convertLogFile(json_data, filename)

        print("DUMPLOG: ", filename)

    # params: user_id
    def display_summary(self, transactionNum, params):
        print("DISPLAY_SUMMARY: ", params)
        UserCommandType().log((round(time.time()*1000)), "Worker", transactionNum, "DISPLAY_SUMMARY")


    def unknown_cmd(self, params):

        # TODO
        # log ErrorEventType.log

        print("UNKNOWN COMMAND!")

    def handle_command(self, transactionNum, cmd, params):
        
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

        # TODO
        # Log UserCommandType.log

        # Call the function to handle the command
        func(transactionNum, params)