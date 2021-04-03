import rabbit_threads
import uuid
import queue
import threading
import time
import os
import pika

confirms_recv = 0


def send_command(requested_command):
    """Send commands to the backend.
        Returns the response.
        Blocking.
    """
    global confirms_recv

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host="rabbitmq")
    )
    publisher_channel = connection.channel()
    consume_channel = connection.channel()

    publisher_channel.exchange_declare(
        exchange=os.environ["FRONTEND_EXCHANGE"]
    )

    consume_channel.exchange_declare(
        exchange=os.environ["CONFIRMS_EXCHANGE"],
        exchange_type='fanout'
    )

    result = consume_channel.queue_declare(queue='')
    queue_name = result.method.queue
    consume_channel.queue_bind(
        exchange=os.environ["CONFIRMS_EXCHANGE"],
        queue=queue_name
    )

    publisher_channel.basic_publish(
        exchange=os.environ["FRONTEND_EXCHANGE"],
        routing_key="frontend",
        body=requested_command,
        properties=pika.BasicProperties(),
        mandatory=True
    )

    print(f"Successfully sent command to publish queue: {requested_command}")
    print("Waiting to get response from consume queue...")

    message = None
    while message is None:
        method_frame, header_frame, message = consume_channel.basic_get(queue=queue_name)

    message = message.decode('utf-8')
    confirms_recv += 1

    print(f"Total confirms received: {confirms_recv}")
    print(f"Received response from consume queue:"
          f"\n\tOriginal Command: {requested_command}"
          f"\n\tReceived Message: {message}\n")

    connection.close()

    return message[4:]
