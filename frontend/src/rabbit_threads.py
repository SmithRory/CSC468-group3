import threading
import queue
import os
import time

from consumer import Consumer
from publisher import Publisher

def consumer_thread(consume_queue):

    consumer = Consumer(
        queue=consume_queue,
        connection_param="rabbitmq",
        exchange_name=os.environ["CONFIRMS_EXCHANGE"],
        queue_name="frontend",
        routing_key="frontend"
    )

    consumer.run()


def publisher_thread(publish_queue):

    publisher = Publisher(
        connection_param="rabbitmq",
        exchange_name=os.environ["FRONTEND_EXCHANGE"],
        queue = publish_queue
    )

    publisher.run()
