import sys
import os
import socket
import time
from . import parser
from . import quote_cache
from database.logs import QuoteServerType, SystemEventType

QUOTE_ADDRESS = "192.168.4.2"
PORT = 4445 #int(os.environ['QUOTE_SERVER_PORT'])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def quote_server_connect() -> bool:
    global s

    s.settimeout(4)
    s.connect((QUOTE_ADDRESS, PORT))
    s.settimeout(None)
    return True
    print("Unable to connect to legacy quote server")
    return False

def get_quote(uid : str, stock_name : str, transactionNum : int, userCommand : str) -> float:
    global s

    result = quote_cache.cache.get(stock_name, None)
    timestampForLog = round(time.time()*1000)
    
    if result is None or time.time() - result.timestamp >= quote_cache.UPDATE_FREQ:
        command = f'{stock_name}, {uid}\n'

        try:
            s.send(command.encode('utf-8'))
            data = s.recv(1024)
            response = parser.quote_result_parse(data.decode('utf-8'))
            if len(response) < 2 :
                quote_server_connect()
                return get_quote(uid, stock_name, transactionNum, userCommand)

            timestampForLog = time.time()

            quote_cache.cache.update({
                stock_name: quote_cache.Quote
                (
                    stock_name=stock_name,
                    value=response[0],
                    timestamp=timestampForLog
                )
            })

            # update after trying on quote server, update quote server time too
            QuoteServerType().log(transactionNum=transactionNum, price=response[0], stockSymbol=stock_name, username=uid, quoteServerTime=response[3], cryptokey=response[4])

            return response[0] # Only returns the stock price

        except socket.error:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            quote_server_connect()
            return get_quote(uid, stock_name, transactionNum, userCommand)



    # add user funds after confirming
    # System Event log since received from cache

    SystemEventType().log(transactionNum=transactionNum, command=userCommand, username=uid, stockSymbol=stock_name)

    return result.value
