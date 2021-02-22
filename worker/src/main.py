import os
import sys
import time
try:
    os.environ["ROUTE_KEY"]
except:
    print("In initial worker container. Waiting to be killed.")
    sys.stdout.flush()
    time.sleep(5)
    sys.exit()

import signal
import pika
import queue
from threading import Thread
from rabbitmq.consumer import Consumer
from rabbitmq.publisher import Publisher
from legacy.parser import command_parse
from cmd_handler import CMDHandler


# Handles exiting when SIGTERM (sent by ^C input) is received
# in a gracefull way. Main loop will only exit after a completed iteration
# so that every service can shut down properly.
EXIT_PROGRAM = False
def exit_gracefully(self, signum, frame):
    global EXIT_PROGRAM
    EXIT_PROGRAM = True
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)

def queue_thread(queue):
     rabbit_queue = Consumer(
         command_queue=queue,
         connection_param='rabbitmq-backend',
         exchange_name=os.environ["BACKEND_EXCHANGE"],
         queue_name=os.environ["ROUTE_KEY"],
         routing_key=os.environ["ROUTE_KEY"]
     )
     rabbit_queue.run()

def main():
    publisher = Publisher()
    publisher.setup_communication()

    message_queue = queue.Queue()
    command_handler = CMDHandler(response_publisher=publisher)

    t_consumer = Thread(target=queue_thread, args=(message_queue,))
    t_consumer.start()

    global EXIT_PROGRAM
    while not EXIT_PROGRAM:
        if not message_queue.empty():
            result = command_parse(message_queue.get())
            command_handler.handle_command(result[0], result[1], result[2])
        sys.stdout.flush()

    t_consumer.join()

if __name__ == "__main__":
    main()
