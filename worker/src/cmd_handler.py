from database.accounts import Accounts, Stocks, AutoTransaction
from database.logs import get_logs, AccountTransactionType, UserCommandType, SystemEventType, ErrorEventType, DebugType
from mongoengine import DoesNotExist
from rabbitmq.publisher import Publisher
from threading import Timer
from math import floor
from legacy import quote, quote_cache, quote_polling
from LogFile import log_handler
import time
import decimal
import time

# TODO: perform atomic updates instead of querying document, modifying it, and then saving it

# TODO: turn dictionaries into cache 

class CMDHandler:

    def __init__(self, response_publisher : Publisher):
        # Response publisher.
        self.response_publisher = response_publisher

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
        self.polling_thread = quote_polling.QuotePollingThread(quote_polling = self.quote_polling, polling_rate = self.POLLING_RATE, response_publisher = response_publisher)
        self.polling_thread.setDaemon(True) # Will be cleaned up on exit.
        self.polling_thread.start()

    # params: user_id, amount
    def add(self, transactionNum, params) -> str:
        amount = params[1]
        user_id = params[0]
        UserCommandType().log(transactionNum=transactionNum, command="ADD", username=user_id, funds=amount)

        # Get the user
        # Note: user.account will return a 'float' if the user
        # has not been created, and 'decimal.Decimal` if they have been.
        if Accounts().user_exists(user_id):
            
            # Update the account.
            update = {
                'inc__account': decimal.Decimal(amount),
                'inc__available': decimal.Decimal(amount)
            }
            ret = Accounts.objects(pk=user_id).update_one(**update)

            # Check the update succeeded.
            if ret != 1:
                err_msg = f"[{transactionNum}] Error: Failed to update account {user_id}."
                print(err_msg)
                ErrorEventType().log(transactionNum=transactionNum, command="ADD", username=user_id, errorMessage=err_msg)
                return err_msg

        else:
            
            # Create the user if they don't exist.
            user = Accounts(user_id=user_id)
            user.account = user.account + amount
            user.available = user.available + amount
            user.save()

            # Log new user.
            DebugType().log(transactionNum=transactionNum, command="ADD", username=user_id, debugMessage=f"Creating user {user_id}.")

        # Log success.
        AccountTransactionType().log(transactionNum=transactionNum, action="add", username=user_id, funds=amount)

        # Notify the user
        ok_msg = f"[{transactionNum}] Successfully added ${amount:.2f} to account {user_id}."
        print(ok_msg)
        return ok_msg

    # params: user_id, stock_symbol
    def quote(self, transactionNum, params) -> str:

        user_id = params[0]
        stock_symbol = params[1]

        UserCommandType().log(transactionNum=transactionNum, command="QUOTE", username=user_id, stockSymbol=stock_symbol)

        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="QUOTE", errorMessage=err_msg)
            return err_msg

        # Get the quote from the stock server
        value = quote.get_quote(user_id, stock_symbol, transactionNum, "QUOTE")

        # Forward the quote to the frontend so the user can see it
        ok_msg = f"[{transactionNum}] {stock_symbol} has value ${value:.2f}."
        print(ok_msg)
        return ok_msg

    # params: user_id, stock_symbol, amount
    def buy(self, transactionNum, params) -> str:

        user_id = params[0]
        stock_symbol = params[1]
        max_debt = float(params[2]) # Maximum dollar amount of the transaction

        UserCommandType().log(transactionNum=transactionNum, command="BUY", username=user_id, stockSymbol=stock_symbol, funds=max_debt)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="BUY", errorMessage=err_msg)
            return err_msg

        # Get a quote for the stock the user wants to buy
        value = quote.get_quote(user_id, stock_symbol, transactionNum, "BUY")

        # Find the number of stocks the user can buy
        num_stocks = floor(max_debt/value) # Ex. max_dept=$100,value=$15per/stock-> num_stocks=6
        if num_stocks==0:
            # Notify the user the stock costs more than the amount given.
            err_msg = f"[{transactionNum}] Error: The price of stock {stock_symbol} ({value:.2f}) is more than the amount requested ({max_debt:.2f})."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="BUY", username=user_id, stockSymbol=stock_symbol, errorMessage=err_msg)
            return err_msg
        
        # Check if the user has enough money available
        trans_price = value*num_stocks
        users_account = Accounts.objects(pk=user_id).only('available').first()
        if trans_price > users_account.available:
            # Notify the user they don't have enough available funds.
            err_msg = f"[{transactionNum}] Error: Insufficient funds to purchase stock {stock_symbol}."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="BUY", username=user_id, stockSymbol=stock_symbol, errorMessage=err_msg)
            return err_msg

        else:
            # Decrement the amount of available funds until a COMMIT or CANCEL happens. This is essentially reserving the funds.
            ret = Accounts.objects(pk=user_id).update_one(inc__available=-decimal.Decimal(trans_price))

            # Check the update succeeded.
            if ret != 1:
                err_msg = f"[{transactionNum}] Error: Failed to update account {user_id}."
                print(err_msg)
                ErrorEventType().log(transactionNum=transactionNum, command="BUY", username=user_id, errorMessage=err_msg)
                return err_msg
        
        # Add the uncommitted buy to the list.
        uncommitted_buy = {user_id: {'stock': stock_symbol, 'num_stocks': num_stocks, 'quote': value, 'amount': max_debt}}
        self.uncommitted_buys.update(uncommitted_buy)
        
        # Cancel any previous timers for this user. There can only be one pending buy at a time.
        previous_timer = self.uncommitted_buy_timers.pop(user_id, None)
        if previous_timer is not None:
            previous_timer.cancel()
            DebugType().log(transactionNum=transactionNum, command="BUY", username=user_id, stockSymbol=stock_symbol, debugMessage="Previous BUY timer cancelled for this user.")

        # Created a new timer to timeout when a COMMIT or CANCEL has not been issued.
        commit_timer = Timer(60.0, self.buy_timeout_handler, [transactionNum, user_id]) # 60 seconds
        commit_timer.start()
        self.uncommitted_buy_timers.update({user_id: commit_timer})
        DebugType().log(transactionNum=transactionNum, command="BUY", username=user_id, stockSymbol=stock_symbol, debugMessage="New BUY timer started for the user.")

        # Forward the user the quote, prompt user to commit or cancel the buy command.
        ok_msg = f'[{transactionNum}] Purchase price ({stock_symbol}): ${value:.2f} per stock x {num_stocks} stocks = ${trans_price:.2f}\nPlease issue COMMIT_BUY or CANCEL_BUY to complete the transaction.'
        print(ok_msg)
        return ok_msg

    # Gets called when a BUY command has timed out (no COMMIT or CANCEL).
    def buy_timeout_handler(self, transactionNum, user_id):

        DebugType().log(transactionNum=transactionNum, command="BUY", username=user_id, debugMessage="BUY command has timed out.")

        # Remove the timer
        timer = self.uncommitted_buy_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()
            DebugType().log(transactionNum=transactionNum, command="BUY", username=user_id, debugMessage="BUY command has timed out")
        
        # Remove the pending buy
        users_buy = self.uncommitted_buys.pop(user_id, None)
        if users_buy is None:
            # Something weird has happened. A buy should not timeout when there is no uncommitted buy command.
            err_msg = f"[{transactionNum}] Error: BUY command has timed out for user {user_id}, but no uncommitted buy was found."
            ErrorEventType(transactionNum=transactionNum, command="BUY", username=user_id, errorMessage=err_msg)
            self.send_response(err_msg)
            return

        # Free the reserved funds.
        ret = Accounts.objects(pk=user_id).update_one(inc__available=decimal.Decimal(users_buy['num_stocks'] * users_buy['quote']))

        # Check the update succeeded.
        if ret != 1:
            err_msg = f"[{transactionNum}] Error: Failed to update account {user_id}."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="BUY", username=user_id, errorMessage=err_msg)
            self.send_response(err_msg)
            return
        
        # Re-issue the buy command.
        self.buy(transactionNum=transactionNum, params=[user_id, users_buy['stock'], users_buy['amount']])
        response_msg = f"[{transactionNum}] BUY command has timed out and will be re-issued."
        DebugType().log(transactionNum=transactionNum, command="BUY", username=user_id, debugMessage=response_msg)
        self.send_response(response_msg)

    # params: user_id
    def commit_buy(self, transactionNum, params) -> str:
        
        user_id = params[0]

        UserCommandType().log(transactionNum=transactionNum, command="COMMIT_BUY", username=user_id)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="COMMIT_BUY", errorMessage=err_msg)
            return err_msg

        # Check to see if the user has issued a buy command.
        users_buy = self.uncommitted_buys.pop(user_id, None)
        if users_buy is None:
            # Must issue a BUY command first
            err_msg = f"[{transactionNum}] Error: Invalid command. A BUY command has not been issued."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="COMMIT_BUY", username=user_id, errorMessage=err_msg)
            return err_msg

        # Cancel the commit timer
        commit_timer = self.uncommitted_buy_timers.pop(user_id, None)
        if commit_timer is not None:
            commit_timer.cancel()
            DebugType().log(transactionNum=transactionNum, command="COMMIT_BUY", username=user_id, debugMessage="BUY timer cancelled for the user")

        # Complete the transaction.
        # Deduct the cost of the purchase. Note: the amount has already been deducted from the available funds.
        cost = decimal.Decimal(users_buy['num_stocks'] * users_buy['quote'])
        user_account = Accounts.objects(pk=user_id).only('stocks', 'account')
        user_account.account = user_account.account - cost
        try:
            users_stock = user_account.stocks.get(symbol=users_buy['stock'])
        except DoesNotExist:
            # Create a new stock.
            new_stock = Stocks(symbol=users_buy['stock'], amount=users_buy['num_stocks'], available=users_buy['num_stocks'])      
            user_account.stocks.append(new_stock)
        else:
            # Increment the existing stock.
            users_stock.amount = users_stock.amount + users_buy['num_stocks']
            users_stock.available = users_stock.available + users_buy['num_stocks']
        user_account.save()

        # Notify the user.
        AccountTransactionType().log(transactionNum=transactionNum, action="remove", username=user_id, funds=cost)
        ok_msg = f"[{transactionNum}] Successfully purchased stock."
        print(ok_msg)
        return ok_msg

    # params: transactionNum, user_id
    def cancel_buy(self, transactionNum, params) -> str:
        
        user_id = params[0]

        UserCommandType().log(transactionNum=transactionNum, command="CANCEL_BUY", username=user_id)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="CANCEL_BUY", errorMessage=err_msg)
            return err_msg

        # Cancel the commit timer
        commit_timer = self.uncommitted_buy_timers.pop(user_id, None)
        if commit_timer is not None:
            commit_timer.cancel()
            DebugType().log(transactionNum=transactionNum, command="CANCEL_BUY", username=user_id, debugMessage="BUY trigger cancelled for this user.")
            
        #Check to see if the user has issued a buy command.
        users_buy = self.uncommitted_buys.pop(user_id, None)
        if users_buy is None:
            # Must issue a BUY command first
            err_msg = f"[{transactionNum}] Error: Invalid command. A BUY command has not been issued."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="CANCEL_BUY", username=user_id, errorMessage=err_msg)
            return err_msg

        # Free the reserved funds.
        ret = Accounts.objects(pk=user_id).update_one(inc__available=decimal.Decimal(users_buy['num_stocks'] * users_buy['quote']))
        # Check the update succeeded.
        if ret != 1:
            err_msg = f"[{transactionNum}] Error: Failed to update account {user_id}."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="CANCEL_BUY", username=user_id, errorMessage=err_msg)
            return err_msg

        # Notify the user.
        ok_msg = f"[{transactionNum}] Successfully cancelled stock purchase."
        print(ok_msg)
        return ok_msg

    # params: user_id, stock_symbol, amount
    def sell(self, transactionNum, params) -> str:

        user_id = params[0]
        stock_symbol = params[1]
        sell_amount = params[2] # dollar amount of the stock to sell

        UserCommandType().log(transactionNum=transactionNum, command="SELL", username=user_id, stockSymbol=stock_symbol, funds=sell_amount)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="SELL", errorMessage=err_msg)
            print(err_msg)
            return err_msg

        # Get a quote for the stock the user wants to sell
        value = quote.get_quote(user_id, stock_symbol, transactionNum, "SELL")

        # Find the number of stocks the user owns.
        users_account = Accounts.objects(pk=user_id).only('stocks').first()
        users_stock = None
        try:
            users_stock = users_account.stocks.get(symbol=stock_symbol)
            if users_stock.amount == 0: # Remove this stock since it's empty.
                ret = Accounts.objects.find(pk=user_id).update(pull__stocks__symbol=stock_symbol)
                if ret != 1:
                    print(f"[{transactionNum}] Error: (Sell) Could not remove empty stock from account {user_id}.")
        except DoesNotExist:
            # The user does not own any of the stock they want to sell.
            err_msg = f"[{transactionNum}] Error: Invalid SELL command. The stock {stock_symbol} is not owned."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="SELL", username=user_id, stockSymbol=stock_symbol, funds=sell_amount, errorMessage=err_msg)
            return err_msg
        
        # Check if the user has enough of the given stock.
        num_to_sell = floor( sell_amount / value )
        if num_to_sell > users_stock.available:
            # The user does not own enough of this stock
            err_msg = f"[{transactionNum}] Error: Insufficient number of stocks owned. Stocks needed ({num_to_sell}), stocks available ({users_stock.available})."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="SELL", username=user_id, stockSymbol=stock_symbol, funds=sell_amount, errorMessage=err_msg)
            return err_msg

        # Add the uncommitted sell to the list.
        uncommitted_sell = {user_id: {'stock': stock_symbol, 'num_stocks': num_to_sell, 'quote': value, 'amount': sell_amount}}
        self.uncommitted_sells.update(uncommitted_sell)

        # Set aside the needed number of stocks.
        ret = Accounts.objects.find(pk=user_id, stocks__symbol=stock_symbol).update(inc__stocks__S__available=-decimal.Decimal(num_to_sell))
        # Check the update succeeded.
        if ret != 1:
            err_msg = f"[{transactionNum}] Error: Failed to update account {user_id}."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="SELL", username=user_id, errorMessage=err_msg)
            return err_msg

        # Cancel any previous timers for this user. There can only be one pending sell at a time.
        previous_timer = self.uncommitted_sell_timers.pop(user_id, None)
        if previous_timer is not None:
            previous_timer.cancel()
            DebugType().log(transactionNum=transactionNum, command="SELL", username=user_id, stockSymbol=stock_symbol, funds=sell_amount, debugMessage="Previous SELL timer cancelled for this user")

        # Created a new timer to timeout when a COMMIT or CANCEL has not been issued.
        commit_timer = Timer(60.0, self.sell_timeout_handler, [transactionNum, user_id]) # 60 seconds
        commit_timer.start()
        self.uncommitted_sell_timers.update({user_id: commit_timer})
        DebugType().log(transactionNum=transactionNum, command="SELL", username=user_id, stockSymbol=stock_symbol, funds=sell_amount, debugMessage="New SELL timer started for this user")

        # Forward the user the transaction info, prompt user to commit or cancel the buy command.
        ok_msg = (
            f'[{transactionNum}] Selling price ({stock_symbol}): ${value:.2f} per stock x {num_to_sell} stocks = ${(value*num_to_sell):.2f}\n'
            f'Please issue COMMIT_SELL or CANCEL_SELL to complete the transaction.'
        )
        print(ok_msg)
        return ok_msg

    # Gets called when a SELL command has timed out (no COMMIT or CANCEL).
    def sell_timeout_handler(self, transactionNum, user_id):

        # Remove the timer.
        timer = self.uncommitted_sell_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()
            DebugType().log(transactionNum=transactionNum, command="SELL", username=user_id, debugMessage="SELL command has timed out")

        # Remove the pending sell.
        users_sell = self.uncommitted_sells.pop(user_id, None)
        if users_sell is None:
            # Something weird has happened. A buy should not timeout when there is no uncommitted buy command.
            err_msg = f"[{transactionNum}] Error: SELL command has timed out for user {user_id}, but no uncommitted sell was found."
            ErrorEventType(transactionNum=transactionNum, command="BUY", username=user_id, errorMessage=err_msg)
            print(err_msg)
            self.send_response(err_msg)
            return

        # Free the reserved stocks.
        ret = Accounts.objects.find(pk=user_id, stocks__symbol=users_sell['stock']).update(inc__stocks__S__available=decimal.Decimal(users_sell['num_stocks']))
        # Check the update succeeded.
        if ret != 1:
            err_msg = f"[{transactionNum}] Error: (SellTimeout) Failed to free reserved stocks for {user_id}."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="SELL", username=user_id, errorMessage=err_msg)
            self.send_response(err_msg)
            return

        # Notify the user their SELL has expired.
        ok_msg = f"[{transactionNum}] The SELL command has expired and will be re-issued."
        print(ok_msg)
        self.send_response(ok_msg)

        # Re-issue the SELL command.
        self.sell(transactionNum = transactionNum, params = [user_id, users_sell['stock'], users_sell['amount']])
        DebugType().log(transactionNum=transactionNum, command="SELL", username=user_id, debugMessage=ok_msg)

    # params: user_id
    def commit_sell(self, transactionNum, params) -> str:

        user_id = params[0]

        UserCommandType().log(transactionNum=transactionNum, command="COMMIT_SELL", username=user_id)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="COMMIT_SELL", errorMessage=err_msg)
            print(err_msg)
            return err_msg

        # Check to see if the user has issued a sell command.
        users_sell = self.uncommitted_sells.pop(user_id, None)
        if users_sell is None:
            # Must issue a SELL command first.
            err_msg = f"[{transactionNum}] Error: Invalid command. Must issue a SELL command first."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="COMMIT_SELL", username=user_id, errorMessage=err_msg)
            return err_msg
        
        # Cancel the commit timer.
        timer = self.uncommitted_sell_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()
            DebugType().log(transactionNum=transactionNum, command="COMMIT_SELL", username=user_id, debugMessage="SELL timer is cancelled for this user")

        # Complete the transaction.
        profit = decimal.Decimal(users_sell['num_stocks'] * users_sell['quote'])
        update = {
            'inc__stocks__S__amount': -users_sell['num_stocks'],
            'inc__account': profit,
            'inc_available': profit
        }
        ret = Accounts.objects.find(pk=user_id, stocks__symbol=users_sell['stock']).update(**update)
        # Check if the account updated.
        if ret != 1:
            err_msg = f"[{transactionNum}] Error: (CommitSell) Failed to update account {user_id}."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="COMMIT_SELL", username=user_id, errorMessage=err_msg)
            return err_msg

        AccountTransactionType().log(transactionNum=transactionNum, action="add", username=user_id, funds=profit)

        # Notify the users.
        ok_msg = f"[{transactionNum}] Successfully sold ${profit:.2f} of stock {users_sell['stock']}."
        print(ok_msg)
        return ok_msg

    # params: user_id
    def cancel_sell(self, transactionNum, params) -> str:

        user_id = params[0]

        UserCommandType().log(transactionNum=transactionNum, command="CANCEL_SELL", username=user_id)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="CANCEL_SELL", errorMessage=err_msg)
            print(err_msg)
            return err_msg

        # Cancel the timer.
        timer = self.uncommitted_sell_timers.pop(user_id, None)
        if timer is not None:
            timer.cancel()
            DebugType().log(transactionNum=transactionNum, command="CANCEL_SELL", username=user_id, debugMessage="SELL timer is cancelled for this user")

        # Check to see if the user has issued a SELL command.
        users_sell = self.uncommitted_sells.pop(user_id, None)
        if users_sell is None:
            # Must issue a SELL command.
            err_msg = f"[{transactionNum}] Error: Invalid command. A SELL command has not been issued."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="CANCEL_SELL", username=user_id, errorMessage=err_msg)
            return err_msg

        # Free the reserved stocks.
        ret = Accounts.objects.find(pk=user_id, stocks__symbol=users_sell['stock']).update(inc__stocks__S__available=decimal.Decimal(users_sell['num_stocks']))
        # Check if the update worked.
        if ret != 1:
            err_msg = f"[{transactionNum}] Error: (CancelSell) Failed to update account {user_id}."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="CANCEL_SELL", username=user_id, errorMessage=err_msg)
            return err_msg

        # Notify the user.
        ok_msg = f"[{transactionNum}] Successfully cancelled sell transaction."
        print(ok_msg)
        DebugType().log(transactionNum=transactionNum, command="CANCEL_SELL", username=user_id, debugMessage=ok_msg)
        return ok_msg

    # params: user_id, stock_symbol, amount
    def set_buy_amount(self, transactionNum, params) -> str:

        user_id = params[0]
        stock_symbol = params[1]
        buy_amount = round(params[2]) # Can only buy a whole number of shares.

        UserCommandType().log(transactionNum=transactionNum, command="SET_BUY_AMOUNT", username=user_id, stockSymbol=stock_symbol, funds=buy_amount)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="SET_BUY_AMOUNT", errorMessage=err_msg)
            print(err_msg)
            return err_msg

        # Add the stock and amount to the user's auto_buy list
        users_account = Accounts.objects.get(pk=user_id)
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
        DebugType().log(transactionNum=transactionNum, command="SET_BUY_AMOUNT", username=user_id, stockSymbol=stock_symbol, funds=buy_amount, debugMessage="AUTO BUY amount is now set, trigger reset as needed")

        # Notify the user.
        ok_msg = f"[{transactionNum}] Successfully set to buy {buy_amount} stocks of {stock_symbol} automatically. Please issue SET_BUY_TRIGGER to set the trigger price."
        print(ok_msg)
        return ok_msg

    # params: user_id, stock_symbol, amount
    def set_buy_trigger(self, transactionNum, params) -> str:

        user_id = params[0]
        stock_symbol = params[1]
        buy_trigger = params[2]

        UserCommandType().log(transactionNum=transactionNum, command="SET_BUY_TRIGGER", username=user_id, stockSymbol=stock_symbol, funds=buy_trigger)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="SET_BUY_TRIGGER", errorMessage=err_msg)
            print(err_msg)
            return err_msg

        # Check the user has issued a SET_BUY_AMOUNT for the given stock.
        users_account = Accounts.objects.get(pk=user_id)
        users_auto_buy = None
        try:
            users_auto_buy = users_account.auto_buy.get(symbol=stock_symbol)
        except DoesNotExist:
            # No SET_BUY_AMOUNT issued.
            err_msg = f"[{transactionNum}] Error: Invalid command. A SET_BUY_AMOUNT must be issued for stock {stock_symbol} before a trigger can be set."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="SET_BUY_TRIGGER", username=user_id, stockSymbol=stock_symbol, funds=buy_trigger, errorMessage=err_msg)
            return err_msg

        # Check the user's account has enough money available.
        transaction_price = round(buy_trigger * users_auto_buy.amount, 2)
        if transaction_price > users_account.available:
            # Insufficient funds.
            err_msg = f"[{transactionNum}] Error: Invalid buy trigger. Insufficient funds for an auto buy. Funds available (${users_account.available:.2f}), auto buy cost (${transaction_price:.2f})."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="SET_BUY_TRIGGER", username=user_id, stockSymbol=stock_symbol, funds=buy_trigger, errorMessage=err_msg)
            return err_msg

        # Set the auto buy trigger.
        users_auto_buy.trigger = buy_trigger
        DebugType().log(transactionNum=transactionNum, command="SET_BUY_TRIGGER", username=user_id, stockSymbol=stock_symbol, funds=buy_trigger, debugMessage="AUTO BUY trigger is set")

        # Deduct money from the available account
        users_account.available = users_account.available - decimal.Decimal(transaction_price)
        users_account.save()

        # Add the user to the list of auto_buys for the stock
        self.quote_polling.add_user_autobuy(user_id=user_id, stock_symbol=stock_symbol, transactionNum=transactionNum, command="SET_BUY_TRIGGER")

        # Notify user.
        ok_msg = f"[{transactionNum}] Successfully set an auto buy for {users_auto_buy.amount} stocks of {stock_symbol} at ${buy_trigger:.2f} per stock."
        print(ok_msg)
        return ok_msg

    # params: user_id, stock_symbol
    def cancel_set_buy(self, transactionNum, params) -> str:

        user_id = params[0]
        stock_symbol = params[1]

        UserCommandType().log(transactionNum=transactionNum, command="CANCEL_SET_BUY", username=user_id, stockSymbol=stock_symbol)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="CANCEL_SET_BUY", errorMessage=err_msg)
            print(err_msg)
            return err_msg

        # Check to see if the user has an auto buy for this stock.
        users_account = Accounts.objects.get(pk=user_id)
        users_auto_buy = None
        try:
            users_auto_buy = users_account.auto_buy.get(symbol=stock_symbol)
        except DoesNotExist:
            # User hasn't set up and auto buy.
            err_msg = f"[{transactionNum}] Error: Invalid command. No auto-buy setup for stock {stock_symbol}."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="CANCEL_SET_BUY", username=user_id, stockSymbol=stock_symbol, errorMessage=err_msg)
            return err_msg

        # Remove the auto buy. Add the reserved funds.
        users_account.auto_buy.remove(users_auto_buy)
        users_account.available = users_account.available + decimal.Decimal(users_auto_buy.amount * users_auto_buy.trigger)
        users_account.save()
        DebugType().log(transactionNum=transactionNum, command="CANCEL_SET_BUY", username=user_id, stockSymbol=stock_symbol, debugMessage="Auto BUY has been cancelled.")

        # Remove the user from the stock polling
        self.quote_polling.get_user_autobuy(user_id = user_id, stock_symbol = stock_symbol)

        # Notify user.
        ok_msg = f"[{transactionNum}] Successfully cancelled the auto buy for stock {stock_symbol}."
        print(ok_msg)
        return ok_msg

    # params: user_id, stock_symbol, amount
    def set_sell_amount(self, transactionNum, params) -> str:

        user_id = params[0]
        stock_symbol = params[1]
        sell_amount = floor(params[2]) # Can only sell a whole number of shares.

        UserCommandType().log(transactionNum=transactionNum, command="SET_SELL_AMOUNT", username=user_id, stockSymbol=stock_symbol, funds=sell_amount)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="SET_SELL_AMOUNT", errorMessage=err_msg)
            print(err_msg)
            return err_msg

        users_account = Accounts.objects.get(pk=user_id)

        # Verify the user owns enough shares of the given stock.
        users_stock = None
        try:
            users_stock = users_account.stocks.get(symbol=stock_symbol)
        except DoesNotExist:
            # The user does not own any of the stock they want to sell.
            err_msg = f"[{transactionNum}] Error: Invalid command. The stock {stock_symbol} is not owned."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="SET_SELL_AMOUNT", username=user_id, stockSymbol=stock_symbol, funds=sell_amount, errorMessage=err_msg)
            return err_msg

        if users_stock.available < sell_amount:
            err_msg = f"[{transactionNum}] Error: Invalid command. Number of available stocks for {stock_symbol} is {users_stock.available} and is less than the amount set to sell {sell_amount}."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="SET_SELL_AMOUNT", username=user_id, stockSymbol=stock_symbol, funds=sell_amount, errorMessage=err_msg)
            return err_msg

        # Decrement the number of available shares.
        users_stock.available = users_stock.available - decimal.Decimal(sell_amount)
        users_account.save()

        # Add the auto sell to the dictionary until the SET_SELL_TRIGGER is received.
        pending_auto_sell = {(user_id,stock_symbol): {'sell_amount': sell_amount}}
        self.pending_sell_triggers.update(pending_auto_sell)
        DebugType().log(transactionNum=transactionNum, command="SET_SELL_AMOUNT", username=user_id, stockSymbol=stock_symbol, funds=sell_amount, debugMessage="AUTO SELL amount is now set, trigger reset as needed")

        # Notify the user.
        ok_msg = f"[{transactionNum}] Successfully set to sell {sell_amount} stocks of {stock_symbol} automatically. Please issue SET_SELL_TRIGGER to set the trigger price."
        print(ok_msg)
        return ok_msg

    # params: user_id, stock_symbol, amount
    def set_sell_trigger(self, transactionNum, params) -> str:

        user_id = params[0]
        stock_symbol = params[1]
        sell_trigger = params[2]

        UserCommandType().log(transactionNum=transactionNum, command="SET_SELL_TRIGGER", username=user_id, stockSymbol=stock_symbol, funds=sell_trigger)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="SET_SELL_TRIGGER", errorMessage=err_msg)
            print(err_msg)
            return err_msg

        # Check the user has issued a SET_SELL_AMOUNT
        pending_auto_sell = self.pending_sell_triggers.pop((user_id,stock_symbol), None)
        if pending_auto_sell is None:
            err_msg = f"[{transactionNum}] Error: Invalid command. Issue a SET_SELL_AMOUNT for this stock before setting the trigger price."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="SET_SELL_TRIGGER", username=user_id, stockSymbol=stock_symbol, funds=sell_trigger, errorMessage=err_msg)
            return err_msg

        # Create the auto_sell
        users_account = Accounts.objects.get(pk=user_id)
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
            DebugType().log(transactionNum=transactionNum, command="SET_SELL_TRIGGER", username=user_id, stockSymbol=stock_symbol, funds=sell_trigger, debugMessage="AUTO SELL trigger is set")

            users_stocks = users_account.stocks.get(symbol=stock_symbol)
            users_stocks.available = users_stocks.available + prev_stock_amount - users_auto_sell.amount

        users_account.save()

        # Add user to the list of auto_sells for the stock
        self.quote_polling.add_user_autosell(user_id = user_id, stock_symbol = stock_symbol, transactionNum=transactionNum, command="SET_SELL_TRIGGER")

        # Notify the user
        ok_msg = f"[{transactionNum}] Successfully set an auto sell for ${pending_auto_sell['sell_amount']} stocks of {stock_symbol} when the price is at least ${sell_trigger:.2f} per stock."
        print(ok_msg)
        return ok_msg

    # params: user_id, stock_symbol
    def cancel_set_sell(self, transactionNum, params) -> str:

        user_id = params[0]
        stock_symbol = params[1]

        UserCommandType().log(transactionNum=transactionNum, command="CANCEL_SET_SELL", username=user_id, stockSymbol=stock_symbol)

        # Check if the user exists.
        if not Accounts().user_exists(user_id=user_id):
            # Invalid command.
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            ErrorEventType().log(transactionNum=transactionNum, command="CANCEL_SET_SELL", errorMessage=err_msg)
            print(err_msg)
            return err_msg

        bad_cmd = True
        reserved_amount = 0
        users_account = Accounts.objects.get(pk=user_id)

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
            except:
                # No auto sell.
                pass
            else:
                # Remove the auto sell.
                users_account.auto_sell.remove(users_auto_sell)
                DebugType().log(transactionNum=transactionNum, command="CANCEL_SET_SELL", username=user_id, stockSymbol=stock_symbol, debugMessage="AUTO SELL is removed for this user")
                reserved_amount = users_auto_sell.amount
                bad_cmd = False
        
        if bad_cmd == True:
            # No SET_SELL commands have been issued.
            err_msg = f"[{transactionNum}] Error: Invalid command. No auto sell has been setup for stock {stock_symbol}."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="CANCEL_SET_SELL", username=user_id, stockSymbol=stock_symbol, errorMessage=err_msg)
            return err_msg

        # Release the reserved stocks.
        users_stocks = users_account.stocks.get(symbol=stock_symbol)
        users_stocks.available = users_stocks.available + reserved_amount
        users_account.save()

        # Remove the user from the auto_sell list
        self.quote_polling.get_user_autosell(user_id = user_id, stock_symbol = stock_symbol)

        # Notify user.
        ok_msg = f"[{transactionNum}] Successfully cancelled automatic selling of stock {stock_symbol}."
        print(ok_msg)
        return ok_msg

    # params: filename, user_id(optional)
    def dumplog(self, transactionNum, params) -> str:

        # Add functionality for handling user id
        # use user_id here to get data from databaseCA
        filename = params[0]
        UserCommandType().log(transactionNum=transactionNum, command="DUMPLOG", filename=filename)

        json_data = get_logs() #this will be logs we get from the database
        log_handler.convertLogFile(json_data, filename)

        ok_msg = f"[{transactionNum}] Successfully wrote logs to {filename}."
        print(ok_msg)
        return ok_msg

    # params: user_id
    def display_summary(self, transactionNum, params) -> str:
        user_id = params[0]

        UserCommandType().log(transactionNum=transactionNum, command="DISPLAY_SUMMARY", username=user_id)

        try:
            user_account = Accounts.objects(pk=user_id)
        except:
            err_msg = f"[{transactionNum}] Error: User {user_id} does not exist."
            print(err_msg)
            ErrorEventType().log(transactionNum=transactionNum, command="DISPLAY_SUMMARY", errorMessage=err_msg)
            return err_msg

        ok_msg = (
            f"[{transactionNum}] User Account Summary:\n"
            f"{user_account.to_json()}"
        )
        print(ok_msg)
        return ok_msg

    def unknown_cmd(self, transactionNum, cmd) -> str:
        err_msg = f"[{transactionNum}] Error: Unknown Command. {cmd}"
        ErrorEventType().log(transactionNum=transactionNum, command="UNKNOWN_COMMAND", errorMessage=err_msg)
        print(err_msg)
        return err_msg

    def send_response(self, response_msg: str):
        '''
        Sends responses back to the manager. 
        This is only used by functions that are not called directly by user commands.
        Ex. When a BUY times out, this needs to be sent to the manager.
        '''
        self.response_publisher.send(response_msg)

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
        
        # Handle the command.
        response = ''
        if func == self.unknown_cmd:
            response = self.unknown_cmd(transactionNum=transactionNum, cmd=cmd)
        else:
            response = func(transactionNum, params)

        # Send the response back.
        self.response_publisher.send(response)
