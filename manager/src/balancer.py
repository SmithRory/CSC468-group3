from worker import UserIds
from parser import Command, parse_command
from threading import Thread
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

        self._send_address = "rabbitmq-backend"
        self._exchange = os.environ["BACKEND_EXCHANGE"]
        self._connection = None
        self._channel = None

    def setup_backend_communication(self):
        while True:
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
                return

            except pika.exceptions.AMQPChannelError as err:
                print(f"Failed to connect to rabbitmq-backend with error {err}")
                time.sleep(2)
            except pika.exceptions.AMQPConnectionError:
                print("Failed to connect to rabbitmq-backend")
                time.sleep(2)

    ''' Blocking function that connects to frontend and backend rabbit queue
    and then begins listening for incoming commands. 
    '''
    def run(self):
        self.setup_backend_communication()
        
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
                routing_key = self.assign_worker(command.uid)

        self._channel.basic_publish(
            exchange=self._exchange,
            routing_key=routing_key,
            body=message,
            properties=pika.BasicProperties()
        )
        print(f"Sent message to {routing_key}")

    ''' Assigns a uid to a worker. Returns the routing key for the assigned worker'''
    def assign_worker(self, uid: str) -> str:
        minimum = len(self.workers[0].commands)
        best_worker = self.workers[0]

        for worker in self.workers:
            if (length := len(worker.commands)) < minimum:
                minimum = length
                best_worker = worker

        for user in self.user_ids:
            if user.user_id == uid:
                print(f"Assigned worker {best_worker.container_id}")
                user.last_seen = time.time()
                user.assigned_worker = best_worker.container_id
                return best_worker.route_key

        print(f"First contact with user {uid}")
        print(f"Assigned worker {best_worker.container_id}")
        self.user_ids.append(UserIds(
            user_id=uid,
            assigned_worker=best_worker.container_id,
            last_seen=time.time()
        ))

        return best_worker.route_key