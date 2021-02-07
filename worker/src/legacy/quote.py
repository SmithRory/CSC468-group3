import sys
import os
import socket
import time
# import parser

QUOTE_ADDRESS = "quoteserver.seng.uvic.ca"
PORT = int(os.environ['QUOTE_SERVER_PORT'])

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((QUOTE_ADDRESS, PORT))
except:
    print("Unable to connect to legacy quote server")
    sys.stdout.flush()

def get_quote(uid : str, stock : str) -> float:
    return 100.0

    command = f'QUOTE,{uid},{stock}\n'

    s.send(command.encode('utf-8'))
    data = s.recv(1024)

    temp = 1.0

    #TODO figure out and parse result from quote server
    # parsed_commands = command_parse(data.decode('utf-8'))
    return temp