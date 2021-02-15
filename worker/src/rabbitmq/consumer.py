import sys
import os
import pika
import queue
import time
import functools

''' Encapsulates Rabbitmq interactions.
Initialization is handled by a sequence of callback functions that are
call by Rabbitmq. Consumers functions can be read from top to bottom 
as that is the order they are called by Rabbitmq.

'''
class Consumer():
    def __init__(self, command_queue, connection_param, exchange_name, queue_name, routing_key):
        self._connection = None
        self._channel = None
        self._commands = command_queue
        self._connection_param = connection_param
        self._exchange_name = exchange_name
        self._queue_name = queue_name
        self._routing_key = routing_key

    ''' Blocking function that initializes a connection to Rabbitmq
    and begins listening for messages. Should only be called once and
    should block for the entirety of the runtime.
    '''
    def run(self):
        self.connect()
        self._connection.ioloop.start()

    def connect(self):
        # amqp://guest:guest@localhost:15672/%2F
        self._connection = pika.SelectConnection(
            parameters=pika.ConnectionParameters(self._connection_param),
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed
        )

    def on_connection_open_error(self, _unused_connection, err):
        self._connection.ioloop.stop()
        time.sleep(2)
        self.run()

    def on_connection_closed(self, _unused_connection, reason):
        self._connection.ioloop.stop()
        time.sleep(2)
        self.run()

    def on_connection_open(self, _unused_connection):
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        self._channel = channel

        cb = functools.partial(self.on_exchange_declareok, userdata=self._exchange_name)
        self._channel.exchange_declare(exchange=self._exchange_name, callback=cb)

    def on_exchange_declareok(self, _unused_frame, userdata):
        cb = functools.partial(self.on_queue_declareok, userdata=self._queue_name)
        self._channel.queue_declare(
            queue=self._queue_name,
            callback=cb,
            exclusive=True
            )

    def on_queue_declareok(self, _unused_frame, userdata):
        cb = functools.partial(self.on_bindok, userdata=self._queue_name)
        self._channel.queue_bind(
            exchange=self._exchange_name,
            queue=self._queue_name,
            routing_key=self._routing_key,
            callback=cb
        )

    def on_bindok(self, _unused_frame, userdata):
        self._channel.basic_qos(
            prefetch_count=1, callback=self.on_basic_qos_ok
        )

    def on_basic_qos_ok(self, _unused_frame):
        self._channel.basic_consume(
            queue=self._queue_name,
            on_message_callback=self.queue_callback,
            auto_ack=True
        )

    ''' Gets called when queue has a message '''
    def queue_callback(self, ch, method, properties, body):
        self._commands.put(body.decode())