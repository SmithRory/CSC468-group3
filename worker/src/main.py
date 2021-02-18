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
# from database.logs import LogType

# Handles exiting when SIGTERM (sent by ^C input) is received 
# in a gracefull way. Main loop will only exit after a completed iteration
# so that every service can shut down properly. 
EXIT_PROGRAM = False
def exit_gracefully(self, signum, frame):
    global EXIT_PROGRAM
    EXIT_PROGRAM = True
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)

message_queue = queue.Queue()
rabbit_queue = Consumer(
    command_queue=message_queue,
    connection_param='rabbitmq-commands',
    exchange_name='backend',
    queue_name='backend_queue',
    routing_key='backend_queue'
)

command_handler = CMDHandler()

def main():
    t_consumer = Thread(target=rabbit_queue.run)
    t_consumer.start()
    transactionNum = 1 # to track the number of the transaction, for logging all logs of the same transaction must have the same number
    # transactionNum needs to change, should ideally be in the load balancer that handles distributing the commands

    log = LogType().save() #should be in manager, starting off the log document/object
    i = 0
    global EXIT_PROGRAM
    while not EXIT_PROGRAM:
        if not message_queue.empty():
            i = i+1
            result = command_parse(message_queue.get())
            
            start_time = time.time()
            command_handler.handle_command(transactionNum, result[0], result[1])
            transactionNum = transactionNum + 1
            
            if i%100 == 0:
                print(f"Finished {i} commands")
                sys.stdout.flush()

    t_consumer.join()

if __name__ == "__main__":
    main()
