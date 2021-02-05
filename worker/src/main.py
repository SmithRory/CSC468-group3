import signal
import sys
import os
import pika
import queue
import time
from threading import Thread, Lock

# Handles exiting when SIGTERM (sent by ^C input) is received 
# in a gracefull way. Main loop will only exit after a completed iteration
# so that every service can shut down properly. 
EXIT_PROGRAM = False
def exit_gracefully(self, signum, frame):
    EXIT_PROGRAM = True
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)

mutex = Lock()

messages = []

def queue_callback(ch, method, properties, body) -> None:
    ch.basic_ack(delivery_tag=method.delivery_tag)

    mutex.acquire()
    messages.append(body.decode())
    print(f'Received: {body.decode()}')
    sys.stdout.flush()
    mutex.release()

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='rabbitmq'))
channel = connection.channel()

channel.exchange_declare(exchange='backend')
channel.queue_declare(queue='backend_queue')
channel.queue_bind(exchange='backend', queue='backend_queue')

channel.basic_consume(
    queue='backend_queue',
    on_message_callback=queue_callback
)

if __name__ == "__main__":
    t_consumer = Thread(target=channel.start_consuming)
    t_consumer.start()

    while not EXIT_PROGRAM:
        time.sleep(0.1)

    t_consumer.join()