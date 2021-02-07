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

    # return [tokens[0], (tokens[1], float(tokens[2]))]
    return [tokens[0], tuple(tokens[1:])]

def is_float(input: str):
    try:
        float(input)
        return True
    except ValueError:
        return False