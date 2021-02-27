from worker import UserIds
from parser import Command, parse_command
from threading import Thread, Timer
import time
import os
import pika
import queue
import sys

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

    ''' Connects to frontend and backend rabbit queue
    and then begins listening for incoming commands. 
    '''
    def run(self):
        self.setup()
        self._cleanup_timer = Timer(
            self._CLEANUP_PERIOD,
            self.cleanup,
            args=None,
            kwargs=None
        )
        self._cleanup_timer.start()

    def balance(self, message: str):
        routing_key = None
        command = parse_command(message)

        if command.command == "DUMPLOG":
            while not self.all_workers_finished():
                print("Waiting for all work to be finished before DUMPLOG can be performed...")
                time.sleep(5)
            routing_key = "worker_queue_0"
            print("Sent DUMPLOG to worker_queue_0")
        else:
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

        try:
            self._channel.basic_publish(
                exchange=self._exchange,
                routing_key=routing_key,
                body=message,
                properties=pika.BasicProperties()
            )
        except:
            self.setup()
            self._channel.basic_publish(
                exchange=self._exchange,
                routing_key=routing_key,
                body=message,
                properties=pika.BasicProperties()
            )


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

        print(f"Assigned worker {best_worker.container_id} to {uid}")
        self.user_ids.append(UserIds(
            user_id=uid,
            assigned_worker=best_worker.container_id,
            last_seen=time.time()
        ))

        best_worker.commands.append(number)
        return best_worker.route_key

    ''' Removes users from user_ids list if they havent been seen for USER_TIMEOUT.
    Also prints current activity for all workers and users.
    '''
    def cleanup(self):
        with self.mutex:
            total_length = 0
            for worker in self.workers:
                worker_len = len(worker.commands)
                total_length = total_length + worker_len
                if worker_len > 0:
                    print(worker)
            if total_length > 0:
                print(f"Total active commands: {total_length}")

            print(f"Total active users: {len(self.user_ids)}")

            self.user_ids = [user for user in self.user_ids if (time.time() - user.last_seen < self._USER_TIMEOUT)]

        sys.stdout.flush()

        self._cleanup_timer = Timer(
            self._CLEANUP_PERIOD,
            self.cleanup,
            args=None,
            kwargs=None
        )
        self._cleanup_timer.start()

    def all_workers_finished(self) -> bool:
        with self.mutex:
            for worker in self.workers:
                for _ in worker.commands:
                    return False

        return True
