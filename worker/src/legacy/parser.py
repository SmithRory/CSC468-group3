import sys
import os
import socket
import time

''' Simple parsing of input command in string format
to a command string and tuple containing th rest of the input.
Tuple order will always be (for commands): command, userid, stocksymbol, amount
For log commands: command, userid, filename
'''
def command_parse(command: str):
    tokens = command.split(',')

    for i, t in enumerate(tokens):
        if is_float(t):
            tokens[i] = float(t)
        else:
            tokens[i] = tokens[i].strip()

    # return [tokens[0], (tokens[1], float(tokens[2]))]
    return [tokens[0], tuple(tokens[1:])]

''' Parses the resulting string after requesting a quote
from the legacy quote server.
Server Quote Return Format: “Quote, Stock Symbol, USER NAME, CryptoKey” 
'''
def quote_result_parse(result: str):
    tokens = result.split(',')
    if not is_float(tokens[0]):
        print("Error: quote result not int")
        print(tokens)
        tokens[0] = None
    else:
        tokens[0] = float(tokens[0])
        
    return tokens

def is_float(input: str):
    try:
        float(input)
        return True
    except ValueError:
        return False
