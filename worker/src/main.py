import signal
import sys
import os
import pika
import queue
import time
from threading import Thread

from rabbitmq.consumer import Consumer
from legacy import quote_cache
import cmd_handler

quote_cache.cache.append("TEST")

# Handles exiting when SIGTERM (sent by ^C input) is received 
# in a gracefull way. Main loop will only exit after a completed iteration
# so that every service can shut down properly. 
EXIT_PROGRAM = False
def exit_gracefully(self, signum, frame):
    EXIT_PROGRAM = True
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)

message_queue = queue.Queue()
rabbit_queue = Consumer(
    command_queue=message_queue,
    connection_param='rabbitmq',
    exchange_name='backend',
    queue_name='backend_queue',
    routing_key='backend_queue'
)

cmd_handler.handle_command("QUOTE", ("temp", "temp"))

if __name__ == "__main__":
    t_consumer = Thread(target=rabbit_queue.run)
    t_consumer.start()

    while not EXIT_PROGRAM:
        pass
        if not message_queue.empty():
            print(f"Message: {message_queue.get()}")
            sys.stdout.flush()
        time.sleep(0.1)

    t_consumer.join()