import sys
import os
import pika
import queue
import time


# Gave up implementing since there is a lot to it

class Consumer():
    def __init__(self, command_queue):
        self._connection = None
        self._channel = None
        self._commands = command_queue

    def run(self):
        self.connect()
        self._connection.ioloop.start()

    def connect(self):
        self._connection = pika.SelectConnection(
            parameters=pika.URLParameters('amqp://guest:guest@localhost:15672/%2F'),
            on_open_callback=self.on_connection_open
        )

    def queue_callback(self, ch, method, properties, body) -> None:
        ch.basic_ack(delivery_tag=method.delivery_tag)
        self._commands.put(body.decode())

    def on_connection_open(self):
        self._channel = self._connection.channel(on_open_callback=on_channel_open)

    def on_channel_open(self, channel):
        self._channel.exchange_declare(exchange='backend')

    def on_connection_open_error(self):
        pass

    def on_connection_closed():
        pass

    def on_exchange_declareok(self, _unused_frame, userdata):
        self._channel.queue_declare(queue='backend_queue', callback=self.on_queue_declareok)

    def on_queue_declareok(self, _unused_frame, userdata):
        self._channel.queue_bind(exchange='backend', queue='backend_queue', callback=self.on_bindok)

    def on_bindok(self, _unused_frame, userdata):
        self._channel.basic_qos(
            prefetch_count=1, callback=self.on_basic_qos_ok
        )

    def on_basic_qos_ok(self, _unused_frame):
        self._channel.basic_consume(
            queue='backend_queue',
            on_message_callback=self.queue_callback
        )