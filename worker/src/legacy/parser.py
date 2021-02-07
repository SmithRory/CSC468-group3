import sys
import os
import socket
import time

''' Simple parsing of input command in string format
to a command string and tuple containing th rest of the input.
Tuple order will always be: userid, stocksymbol, amount for commands.
For log commands: userid, filename
'''

stupid_bullshit = "tesasdasfsfdfasdfs"

def command_parse(command: str):
    return ["QUOTE", ("asdfghjkl1", "S")]