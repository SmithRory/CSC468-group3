import signal
import sys
import os
import asyncio
from container_comm import Comm
import time

# Handles exiting when SIGTERM (sent by ^C input) is received 
# in a gracefull way. Main loop will only exit after a completed iteration
# so that every service can shut down properly. 
EXIT_PROGRAM = False
def exit_gracefully(self, signum, frame):
    EXIT_PROGRAM = True
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)

loop = asyncio.get_event_loop()

# comm = Comm()
# loop.run_until_complete(comm.connect())
# loop.run_until_complete(comm.send("test data"))


if __name__ == "__main__":
    
    while not EXIT_PROGRAM:
        time.sleep(1)
        pass