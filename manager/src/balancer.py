from worker import UserIds
from parser import Command, parse_command
from threading import Thread, Timer
import time
import os
import pika
import queue

class Balancer():
    def __init__(self, workers, queue, mutex):
        self.workers = workers
        self.user_ids = []
        self.command_queue = queue
        self.mutex = mutex

        self._cleanup_timer = None
        self._CLEANUP_PERIOD = 15.0 # Seconds
        self._USER_TIMEOUT = 10.0 # Seconds

        self._send_address = "rabbitmq-backend"
        self._exchange = os.environ["BACKEND_EXCHANGE"]
        self._connection = None
        self._channel = None

    def setup(self):
        connected = False
        while not connected:
            print("Attempting to connect to rabbitmq-backend")
            try:
                self._connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=self._send_address,
                        heartbeat=600,
                        blocked_connection_timeout=300)
                )
                self._channel = self._connection.channel()
                self._channel.exchange_declare(exchange=self._exchange)

                print("Connected to rabbitmq-backend")
                connected = True

            except pika.exceptions.AMQPChannelError as err:
                print(f"Failed to connect to rabbitmq-backend with error {err}")
                time.sleep(2)
            except pika.exceptions.AMQPConnectionError:
                print("Failed to connect to rabbitmq-backend")
                time.sleep(2)

        self._cleanup_timer = Timer(
            self._CLEANUP_PERIOD,
            self.cleanup,
            args=None,
            kwargs=None
        )
        self._cleanup_timer.start()

    ''' Blocking function that connects to frontend and backend rabbit queue
    and then begins listening for incoming commands. 
    '''
    def run(self):
        self.setup()
        
        while True:
            if not self.command_queue.empty():
                self.balance(self.command_queue.get())

        print("End of balancer thread")

    def balance(self, message: str):
        print(f"Received message:{message}")

        routing_key = None
        command = parse_command(message)

        with self.mutex:
            for user in self.user_ids:
                if user.user_id == command.uid:
                    for worker in self.workers:
                        if worker.container_id == user.assigned_worker:
                            routing_key = worker.route_key
                            worker.commands.append(command.number)
                            break

                    user.last_seen = time.time()
                    break

            if routing_key is None:
                routing_key = self.assign_worker(command.uid, command.number)

        self._channel.basic_publish(
            exchange=self._exchange,
            routing_key=routing_key,
            body=message,
            properties=pika.BasicProperties()
        )
        print(f"Sent message to {routing_key}")

    ''' Assigns a uid to a worker. Returns the routing key for the assigned worker'''
    def assign_worker(self, uid: str, number: int) -> str:
        minimum = len(self.workers[0].commands)
        best_worker = self.workers[0]

        for worker in self.workers:
            if (length := len(worker.commands)) < minimum:
                minimum = length
                best_worker = worker

        for user in self.user_ids:
            if user.user_id == uid:
                user.last_seen = time.time()
                user.assigned_worker = best_worker.container_id
                best_worker.commands.append(number)
                return best_worker.route_key

        print(f"First contact with user {uid}")
        print(f"Assigned worker {best_worker.container_id} to {uid}")
        self.user_ids.append(UserIds(
            user_id=uid,
            assigned_worker=best_worker.container_id,
            last_seen=time.time()
        ))

        best_worker.commands.append(number)
        return best_worker.route_key

    def cleanup(self):
        with self.mutex:
            print("\n\n")
            for worker in self.workers:
                print(worker)

            for user in self.user_ids:
                print(user)

            self.user_ids = [user for user in self.user_ids if (time.time() - user.last_seen < self._USER_TIMEOUT)]

        self._cleanup_timer = Timer(
            self._CLEANUP_PERIOD,
            self.cleanup,
            args=None,
            kwargs=None
        )
        self._cleanup_timer.start()

