import sys
import os
import pika
import queue
import time
import functools

class Publisher:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._send_address = "rabbitmq-confirm"
        self._exchange = os.environ["CONFIRMS_EXCHANGE"]

    def setup_communication(self):
        while True:
            print("Attempting to connect to rabbitmq-confirm")
            try:
                self._connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=self._send_address,
                        heartbeat=600,
                        blocked_connection_timeout=300
                    )
                )
                self._channel = self._connection.channel()
                self._channel.exchange_declare(exchange=self._exchange)

                print("Connected to rabbitmq-confirm")
                return

            except pika.exceptions.AMQPChannelError as err:
                print(f"Failed to connect to rabbitmq-confirm with error {err}")
                time.sleep(2)
            except pika.exceptions.AMQPConnectionError:
                print("Failed to connect to rabbitmq-confirm")
                time.sleep(2)

    def send(self, message: str):
        self._channel.basic_publish(
            exchange=self._exchange,
            routing_key="confirm",
            body=message,
            properties=pika.BasicProperties()
        )