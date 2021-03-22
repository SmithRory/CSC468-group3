import pika
import functools
import sys

class Publisher():
    QUICK_SEND = 0.01
    SLOW_SEND = 2.0

    def __init__(self, connection_param, exchange_name, queue):
        self._connection = None
        self._channel = None
        self._exchange = exchange_name
        self._connection_param = connection_param

        self.queue = queue
        self._publish_buffer = [] # Tuple(routing_key, message)
        self._deliveries = {}
        self._acked = 0
        self._nacked = 0
        self._message_number = 0

        self._stopping = False

    def connect(self):
        return pika.SelectConnection(
            parameters=pika.ConnectionParameters(self._connection_param),
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed
        )

    def on_connection_open_error(self, _unused_connection, err):
        print(f'{self._connection_param} Connection open failed, reopening in 5 seconds: {err}')
        self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def on_connection_closed(self, _unused_connection, reason):
        print(f'{self._connection_param} Connection closed, reopening in 5 seconds: {reason}')
        self._connection.ioloop.call_later(5, self._connection.ioloop.stop)

    def on_connection_open(self, _unused_connection):
        print(f"{self._connection_param}: on_connection_open")
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        print(f"{self._connection_param}: on_channel_open")
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_closed)
        
        cb = functools.partial(
            self.on_exchange_declareok, userdata=self._exchange
        )
        self._channel.exchange_declare(exchange=self._exchange, callback=cb)

    def on_channel_closed(self, channel, reason):
        print(f"Connection closed: {reason}")
        self._channel = None
        if not self._stopping:
            self._connection.close()

    def on_exchange_declareok(self, _unused_frame, userdata):
        print(f"{self._connection_param}: on_exchange_declareok")
        self.start_publishing()

    def start_publishing(self):
        """This method will enable delivery confirmations and schedule the
        first message to be sent to RabbitMQ
        """
        print(f"{self._connection_param}: Publisher Issuing consumer related RPC commands")
        # self._channel.confirm_delivery(self.on_delivery_confirmation)
        self.schedule_next_message(self.SLOW_SEND)

    def on_delivery_confirmation(self, method_frame):
        conf_message = self._deliveries.get(method_frame.method.delivery_tag)
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()

        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            print(f"Message {conf_message} with type {confirmation_type}")
            sys.stdout.flush()
            self._nacked += 1

    def schedule_next_message(self, publish_interval):
        #self._connection.ioloop.call_soon(self.publish_message)
        self._connection.ioloop.call_later(publish_interval, self.publish_message)

    def publish_message(self):
        if self._channel is None or self.queue.empty():
            self.schedule_next_message(self.SLOW_SEND)
        else:
            data = self.queue.get()

            self._channel.basic_publish(
                exchange=self._exchange,
                routing_key="frontend",
                body=data,
                properties=pika.BasicProperties(),
                mandatory=True
            )

            self.schedule_next_message(self.QUICK_SEND)

    def run(self):
        """Run the example code by connecting and then starting the IOLoop.
        """
        while not self._stopping:
            try:
                self._connection = self.connect()
                self._connection.ioloop.start()
            except KeyboardInterrupt:
                self.stop()
                if (self._connection is not None and not self._connection.is_closed):
                    self._connection.ioloop.start()

        print("Stopping publisher thread")

    def stop(self):
        self._stopping = True
        self.close_channel()
        self.close_connection()

    def close_channel(self):
        if self._channel is not None:
            self._channel.close()

    def close_connection(self):
        if self._connection is not None:
            self._connection.close()
