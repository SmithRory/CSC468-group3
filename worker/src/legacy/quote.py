import sys
import os
import socket
import time

QUOTE_ADDRESS = "quoteserver.seng.uvic.ca"
PORT = int(os.environ['QUOTE_SERVER_PORT'])

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((QUOTE_ADDRESS, PORT))
except:
    print("Unable to connect to legacy quote server")
    sys.stdout.flush()

def get_quote(uid : str, stock : str) -> float:
    command = f'QUOTE,{uid},{stock}\n'

    s.send(command.encode('utf-8'))
    data = s.recv(1024)

    return data.decode('utf-8')