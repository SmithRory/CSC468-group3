import sys
import os
import socket
import time
from . import parser
from . import quote_cache
from database.logs import QuoteServerType, SystemEventType

QUOTE_ADDRESS = "192.168.4.2"
PORT = int(os.environ['QUOTE_SERVER_PORT'])

def get_quote(uid : str, stock_name : str, transactionNum : int, userCommand : str) -> float:
    result = quote_cache.cache.get(stock_name, None)
    timestampForLog = round(time.time()*1000)
    
    if result is None or time.time() - result.timestamp >= quote_cache.UPDATE_FREQ:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((QUOTE_ADDRESS, PORT))
            s.settimeout(None)
        except:
            # This should throw an error but is left this way so it can be
            # tested outside the VM

            QuoteServerType().log(timestampForLog, "Quote", transactionNum, 12334.3, stock_name, uid, timestampForLog, "tempkey")

            print("Unable to connect to legacy quote server")
            return 12345.6

        command = f'QUOTE,{uid},{stock_name}\n'
        s.send(command.encode('utf-8'))
        data = s.recv(1024)
        response = parser.quote_result_parse(data.decode('utf-8'))

        timestampForLog = time.time()

        quote_cache.cache.update({
            stock_name: quote_cache.Quote
            (
                stock_name=stock_name,
                value=result[0],
                timestamp=timestampForLog
            )
        })

        # update after trying on quote server, update quote server time too
        QuoteServerType().log(round(timestampForLog*1000), "Quote", transactionNum, response[0], stock_name, uid, response[3], response[4])

        return response[0] # Only returns the stock price

    # add user funds after confirming
    # System Event log since received from cache

    SystemEventType().log(timestampForLog, "Cache-Quote", transactionNum, userCommand, username=uid, stockSymbol=stock_name)

    return result.value
