import threading
from parser import Command, parse_command
from publisher import Publisher
from threading import Thread, Timer
import time
import os
import pika
import queue
import sys
import random

class Balancer():
    def __init__(self, workers, queue, mutex, runtime_data):
        self.workers = workers
        self._NUM_WORKERS = len(workers)
        self.command_queue = queue
        self.mutex = mutex

        self._cleanup_timer = None
        self._total_commands_seen = 0
        self.runtime_data = runtime_data
        self._prev_active_commands = 0
        self._CLEANUP_PERIOD = 5.0 # Seconds

        self._send_address = "rabbitmq"
        self.publish_queue = None
        self.publisher = None
        self.t_publisher = None

    ''' Connects to frontend and backend rabbit queue
    and then begins listening for incoming commands. 
    '''
    def run(self):
        self.publish_queue = queue.Queue()

        self.publisher = Publisher(
            connection_param=self._send_address,
            exchange_name=os.environ["BACKEND_EXCHANGE"],
            publish_queue = self.publish_queue
        )
        self.t_publisher = threading.Thread(target=self.publisher.run)
        self.t_publisher.start()

        self._cleanup_timer = Timer(
            self._CLEANUP_PERIOD,
            self.cleanup,
            args=None,
            kwargs=None
        )
        self._cleanup_timer.start()

    def balance(self, message: str):
        self._total_commands_seen = self._total_commands_seen + 1
        routing_key = None
        command = parse_command(message)

        if command.command == "DUMPLOG":
            while self.runtime_data.active_commands != 0:
                time.sleep(2)
            routing_key = "worker_queue_0"
            print("Sent DUMPLOG to worker_queue_0")
        else:
            worker_index = abs(hash(command.uid)) % self._NUM_WORKERS
            routing_key = self.workers[worker_index].route_key
            with self.mutex:
                self.runtime_data.active_commands += 1
            # self.workers[worker_index].commands.append(command.number)

        self.publish_queue.put((routing_key, message))

    ''' Removes users from user_ids list if they havent been seen for USER_TIMEOUT.
    Also prints current activity for all workers and users.
    '''
    def cleanup(self):
        # total_length = 0
        # for worker in self.workers:
        #     worker_len = len(worker.commands)
        #     total_length = total_length + worker_len
        #     if worker_len > 0:
        #         print(worker)
        
        # print(f"Total active commands: {self.runtime_data.active_commands}")
        # print(f"TPS: {(self._prev_active_commands-self.runtime_data.active_commands)/self._CLEANUP_PERIOD}")
        # print(f"Total commands seen: {self._total_commands_seen}")

        print("Active: {:>10} | Total: {:>10} | TPS: {:>5}".format(
            self.runtime_data.active_commands, 
            (self._prev_active_commands-self.runtime_data.active_commands)/self._CLEANUP_PERIOD, 
            self._total_commands_seen)
        )

        self._prev_active_commands = self.runtime_data.active_commands

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
