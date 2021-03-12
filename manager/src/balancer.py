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
        self._PRINT_PERIOD = 5.0 # Seconds

        self._send_address = "rabbitmq"
        self.publish_communication = None
        self.publisher = None
        self.t_publisher = None

    ''' Connects to frontend and backend rabbit queue
    and then begins listening for incoming commands. 
    '''
    def run(self):
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

        # print(f"Length of buffer: {len(self._send_buffer)}")

        for message in self._send_buffer:
            self._total_commands_seen = self._total_commands_seen + 1
            routing_key = None
            command = parse_command(message)

            if command.command == "DUMPLOG":
                self.publish_communication.is_empty = False
                while self.runtime_data.active_commands != 0:
                    time.sleep(2)
                routing_key = "worker_queue_0"
                print("Sent DUMPLOG to worker_queue_0")
            else:
                worker_index = abs(hash(command.uid)) % self._NUM_WORKERS
                routing_key = self.workers[worker_index].route_key
                with self.runtime_data.mutex:
                    self.runtime_data.active_commands += 1
                # self.workers[worker_index].commands.append(command.number)

            with self.publish_communication.mutex:
                self.publish_communication.buffer.append((routing_key, message))
                self.publish_communication.length += 1

        self.publish_communication.is_empty = False

    ''' Removes users from user_ids list if they havent been seen for USER_TIMEOUT.
    Also prints current activity for all workers and users.
    '''
    def print_status(self):
        # total_length = 0
        # for worker in self.workers:
        #     worker_len = len(worker.commands)
        #     total_length = total_length + worker_len
        #     if worker_len > 0:
        #         print(worker)
        
        # print(f"Total active commands: {self.runtime_data.active_commands}")
        # print(f"TPS: {(self._prev_active_commands-self.runtime_data.active_commands)/self._PRINT_PERIOD}")
        # print(f"Total commands seen: {self._total_commands_seen}")

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
