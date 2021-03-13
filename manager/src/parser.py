from dataclasses import dataclass
import re

@dataclass
class Command:
    number: int
    command: str
    uid: str
    params: list # List of the remaining parts

def parse_command(command: str) -> Command: 
    whitelist = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ[],0123456789./")
    filtered = ''.join(filter(whitelist.__contains__, command))

    tokens = filtered.split(',')
    if len(tokens) < 2:
        return Command(number=-1, command='', uid='', params=[])

    # number = re.findall(".*?\[(.*)].*", tokens[0])
    # number = int(number[0])
    number = 0 # We dont use the number anymore
    command = tokens[0].split(']')[1]

    if command == "DUMPLOG" and len(tokens) < 3:
        uid = "guest"
    else:
        uid = tokens[1]

    if len(tokens) > 2:
        params = tokens[2:]
    else:
        params = []

    return Command(
        number=number,
        command=command,
        uid=uid,
        params=params
    )
