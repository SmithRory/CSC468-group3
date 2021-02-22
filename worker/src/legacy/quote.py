import sys
import os
import socket
import time
from . import parser
from . import quote_cache
from database.logs import QuoteServerType, SystemEventType

QUOTE_ADDRESS = "192.168.4.2"
PORT = int(os.environ['QUOTE_SERVER_PORT'])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def quote_server_connect():
    global s

    s.settimeout(2)
    s.connect((QUOTE_ADDRESS, PORT))
    s.settimeout(None)

def get_quote(uid : str, stock_name : str, transactionNum : int, userCommand : str) -> float:
    global s

    result = quote_cache.get(stock_name)

    if result is None:
        command = f'{stock_name}, {uid}\n'

        try:
            s.send(command.encode('utf-8'))
            data = s.recv(1024)
            if len(data) < 2 :
                quote_server_connect()
                return get_quote(uid, stock_name, transactionNum, userCommand)

            response = parser.quote_result_parse(data.decode('utf-8'))

            quote_cache.add(stock_name, response[0], response[3])

            QuoteServerType().log(transactionNum=transactionNum, price=response[0], stockSymbol=stock_name, username=uid, quoteServerTime=response[3], cryptokey=response[4])

            return response[0] # Only returns the stock price

        except socket.error:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                quote_server_connect()
            except socket.timeout:
                print("Socket connection timeout")
                time.sleep(0.1) # Just to reduce spam error messages

            return get_quote(uid, stock_name, transactionNum, userCommand)



    # add user funds after confirming
    # System Event log since received from cache
    print("Quote used from cache!!")
    SystemEventType().log(transactionNum=transactionNum, command=userCommand, username=uid, stockSymbol=stock_name)

    return result.value
