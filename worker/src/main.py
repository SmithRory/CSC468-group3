import signal
import sys
import os
import pika
import queue
import time
from threading import Thread
from rabbitmq.consumer import Consumer
from legacy.parser import command_parse
from cmd_handler import CMDHandler

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

command_handler = CMDHandler()

if __name__ == "__main__":
    t_consumer = Thread(target=rabbit_queue.run)
    t_consumer.start()

    while not EXIT_PROGRAM:
        if not message_queue.empty():
            result = command_parse(message_queue.get())
            print(f"result: {result}")
            command_handler.handle_command(result[0], result[1])
            sys.stdout.flush()

    t_consumer.join()