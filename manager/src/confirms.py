from consumer import Consumer
import os
import re
from threading import Lock

class Confirms():
    def __init__(self, workers, mutex):
        self.workers = workers
        self.mutex = mutex

        self._recv_address = "rabbitmq-confirm"
        self._consumer = None

    def connect(self):
        self._consumer = Consumer(
            call_on_callback=self.on_receive,
            connection_param=self._recv_address,
            exchange_name=os.environ["CONFIRMS_EXCHANGE"],
            queue_name="confirm",
            routing_key="confirm"
        )

    def run(self):
        self.connect()
        self._consumer.run()

    def on_receive(self, message):
        print(f"Received confirm: {message}")
        number = re.findall(".*?\[(.*)].*", message)
        number = int(number[0])

        with self.mutex:
            for worker in self.workers:
                print(worker.commands)
                if number in worker.commands:
                    worker.commands.remove(number)
                    print(f"Removing command {number} from commands list")
                    return