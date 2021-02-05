from database.account_dao import Accounts, get_users
from mongoengine import DoesNotExist

def handle_command(cmd, params):
    
    switch = {
        "ADD": add,
        "QUOTE": quote,
        "COMMIT_BUY": commit_buy,
        "CANCEL_BUY": cancel_buy,
        "SELL": sell,
        "COMMIT_SELL": commit_sell,
        "CANCEL_SELL": cancel_sell,
        "SET_BUY_AMOUNT": set_buy_amount, 
        "CANCEL_SET_BUY": cancel_set_buy,
        "SET_BUY_TRIGGER": set_buy_trigger,
        "SET_SELL_AMOUNT": set_sell_amount,
        "SET_SELL_TRIGGER": set_sell_trigger,
        "CANCEL_SET_SELL": cancel_set_sell,
        "DUMPLOG": dumplog,
        "DISPLAY_SUMMARY": display_summary
    }
    
    # Get the function
    func = switch.get(cmd, unknown_cmd)
    # Call the function to handle the command
    func(params)

# params: user_id, amount
def add(params):
    amount = params[1]
    user_id = params[0]

    # Get the user
    try:
        user = Accounts.objects.get(user_id=user_id)
    except DoesNotExist:
        # Make the user if they don't exist
        user = Accounts(user_id=user_id)

    # Update the user accounts
    user.account = user.account + params[1]
    user.available = user.available + params[1]
    
    # Save the user
    try:
        user.save()
        print("Saved user")
    except Exception as e:
        print(e)

# params: user_id, stock_symbol
def quote(params):
    print("QUOTE: ", params)

    # Get the quote from the stock server

    # Forward the quote to the frontend so the user can see it
    

# params: user_id, stock_symbol, amount
def buy(params):

    # Get a quote for the stock the user wants to buy

    # Check if the user has enough available

    # Forward the user the quote and if they have enough money.
    # They should be propted to commit or cancel the buy command.
    
    # Set a timer for one minute. If no commit or cancel has happend
    # then re issue the quote and present the new stock price to the user.

    print("BUY: ", params)

# params: user_id
def commit_buy(params):
    print("COMMIT_BUY: ", params)

# params: user_id
def cancel_buy(params):
    print("CANCEL_BUY: ", params)

# params: user_id, stock_symbol, amount
def sell(params):
    print("SELL: ", params)

# params: user_id
def commit_sell(params):
    print("COMMIT_SELL: ", params)

# params: user_id
def cancel_sell(params):
    print("CANCEL_SELL: ", params)

# params: user_id, stock_symbol, amount
def set_buy_amount(params):
    print("SET_BUY_AMOUNT: ", params)

# params: user_id, stock_symbol
def cancel_set_buy(params):
    print("CANCEL_SET_BUY: ", params)

# params: user_id, stock_symbol, amount
def set_buy_trigger(params):
    print("SET_BUY_TRIGGER: ", params)

# params: user_id, stock_symbol, amount
def set_sell_amount(params):
    print("SET_SELL_AMOUNT: ", params)

# params: user_id, stock_symbol, amount
def set_sell_trigger(params):
    print("SET_SELL_TRIGGER: ", params)

# params: user_id, stock_symbol
def cancel_set_sell(params):
    print("CANCEL_SET_SELL: ", params)

# params: user_id(optional), filename
def dumplog(params):
    print("DUMPLOG: ", params)

# params: user_id
def display_summary(params):
    print("DISPLAY_SUMMARY: ", params)

def unknown_cmd(params):
    print("UNKNOWN COMMAND!")
    
# Should only be used for testing.
if __name__ == "__main__":
    command = "SELL"
    parameters = ("oY01WVirLr", "S", 641.90)
    handle_command(command, parameters)

