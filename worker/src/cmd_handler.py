
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

def add(params):
    print("ADD: ", params)
    
def quote(params):
    print("QUOTE: ", params)

def commit_buy(params):
    print("COMMIT_BUY: ", params)

def cancel_buy(params):
    print("CANCEL_BUY: ", params)

def sell(params):
    print("SELL: ", params)

def commit_sell(params):
    print("COMMIT_SELL: ", params)

def cancel_sell(params):
    print("CANCEL_SELL: ", params)

def set_buy_amount(params):
    print("SET_BUY_AMOUNT: ", params)

def cancel_set_buy(params):
    print("CANCEL_SET_BUY: ", params)

def set_buy_trigger(params):
    print("SET_BUY_TRIGGER: ", params)

def set_sell_amount(params):
    print("SET_SELL_AMOUNT: ", params)

def set_sell_trigger(params):
    print("SET_SELL_TRIGGER: ", params)

def cancel_set_sell(params):
    print("CANCEL_SET_SELL: ", params)

def dumplog(params):
    print("DUMPLOG: ", params)

def display_summary(params):
    print("DISPLAY_SUMMARY: ", params)

def unknown_cmd(params):
    print("UNKNOWN COMMAND!")
    
# Should only be used for testing.
if __name__ == "__main__":
    command = "SELL"
    parameters = ("oY01WVirLr", "S", 641.90)
    handle_command(command, parameters)

