import threading
from parser import Command, parse_command
from publisher import Publisher
from threading import Thread, Timer, Lock
from worker import ThreadCommunication
import time
import os
import pika
import sys
import random
import hashlib
from functools import wraps

class Balancer():
    def __init__(self, workers, communication, runtime_data):
        self.workers = workers
        self._NUM_WORKERS = len(workers)
        self.communication = communication
        self._send_buffer = None

        self._print_status_timer = None
        self._total_commands_seen = 0
        self.runtime_data = runtime_data
        self._prev_active_commands = 0
        self._PRINT_PERIOD = 10.0 # Seconds

        self._send_address = "rabbitmq"
        self.publish_communication = None
        self.publisher = None
        self.t_publisher = None

    ''' Connects to frontend and backend rabbit queue
    and then begins listening for incoming commands. 
    '''
    def setup(self):
        self.publish_communication = ThreadCommunication(
            buffer = [],
            length=0,
            mutex=Lock()
        )

        self.publisher = Publisher(
            connection_param=self._send_address,
            exchange_name=os.environ["BACKEND_EXCHANGE"],
            communication = self.publish_communication
        )
        self.t_publisher = threading.Thread(target=self.publisher.run)
        self.t_publisher.start()

        self._print_status_timer = Timer(
            self._PRINT_PERIOD,
            self.print_status,
            args=None,
            kwargs=None
        )
        self._print_status_timer.start()

    def balance(self):
        with self.communication.mutex:
            self._send_buffer = self.communication.buffer
            self.communication.buffer = []
            self.communication.length = 0

        start = time.time()
        for message in self._send_buffer:
            self._total_commands_seen = self._total_commands_seen + 1
            routing_key = None
            command = parse_command(message)

            if command.command == "DUMPLOG":
                while self.runtime_data.active_commands != 0:
                    time.sleep(5)
                routing_key = "worker_queue_0"
                print("Sent DUMPLOG to worker_queue_0")
            else:
                worker_index = calculate_worker_index(command.uid, self._NUM_WORKERS)

                routing_key = self.workers[worker_index].route_key
                with self.runtime_data.mutex:
                    self.runtime_data.active_commands += 1

            with self.publish_communication.mutex:
                self.publish_communication.buffer.append((routing_key, message))
                self.publish_communication.length += 1

        print(f"balance() took {time.time()-start} to process {len(self._send_buffer)} commands")

    ''' Removes users from user_ids list if they havent been seen for USER_TIMEOUT.
    Also prints current activity for all workers and users.
    '''
    def print_status(self):
        print("Active: {:>10} | Total: {:>10} | TPS: {:>10} |".format(
            self.runtime_data.active_commands, 
            self._total_commands_seen,
            (self._prev_active_commands-self.runtime_data.active_commands)/self._PRINT_PERIOD)
        )

        self._prev_active_commands = self.runtime_data.active_commands

        sys.stdout.flush()

        self._print_status_timer = Timer(
            self._PRINT_PERIOD,
            self.print_status,
            args=None,
            kwargs=None
        )
        self._print_status_timer.start()

    def all_workers_finished(self) -> bool:
        with self.mutex:
            for worker in self.workers:
                for _ in worker.commands:
                    return False

        return True

''' Decorator that caches result of function depending on args
and returns result if its in the cache rather than running 
the function again
'''
def memo(f):
    cache = {}

    @wraps(f)
    def wrap(*arg):
        if arg not in cache:
            cache['arg'] = f(*arg)
        return cache['arg']
    
    return wrap

@memo
def calculate_worker_index(uid: str, NUM_WORKERS: int):
    worker_index = hashlib.sha256(uid.encode('utf-8')).digest()
    worker_index = int.from_bytes(worker_index, byteorder='big', signed=False) % NUM_WORKERS
    return worker_index