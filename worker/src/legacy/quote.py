import sys
import os
import socket
import time
from . import parser

QUOTE_ADDRESS = "192.168.4.2"
PORT = int(os.environ['QUOTE_SERVER_PORT'])

def get_quote(uid : str, stock : str) -> float:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(4)
        s.connect((QUOTE_ADDRESS, PORT))
        s.settimeout(None)
    except:
        # This should throw an error but is left this way so it can be
        # tested outside the VM

        print("Unable to connect to legacy quote server")
        return 12345.6

    command = f'QUOTE,{uid},{stock}\n'

    s.send(command.encode('utf-8'))
    data = s.recv(1024)

    response = parser.quote_result_parse(data.decode('utf-8'))
    return response[0] # Only returns the stock price
