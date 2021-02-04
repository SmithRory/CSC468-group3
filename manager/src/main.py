import docker
import signal
import sys
import os
import time
import pika

client = docker.from_env()
print(client.containers.list())
sys.stdout.flush()

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='rabbitmq'))
channel = connection.channel()

def queue_callback(ch, method, properties, body) -> None:
    print(f'Received: {body.decode()}')
    sys.stdout.flush()
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.exchange_declare(exchange='frontend')
channel.queue_declare(queue='frontend_queue')
channel.queue_bind(exchange='frontend', queue='frontend_queue')
# channel.basic_qos(prefetch_count=1)
channel.basic_consume(
    queue='frontend_queue',
    on_message_callback=queue_callback
)


# Handles exiting when SIGTERM (sent by ^C input) is received 
# in a gracefull way. Main loop will only exit after a completed iteration
# so that every service can shut down properly. 
# EXIT_PROGRAM = False
# def exit_gracefully(self, signum, frame):
#     EXIT_PROGRAM = True
# signal.signal(signal.SIGINT, exit_gracefully)
# signal.signal(signal.SIGTERM, exit_gracefully)

if __name__ == "__main__":
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.close()
