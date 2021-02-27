import signal
import sys
import os
import time
import docker
import queue
from threading import Thread, Lock
from consumer import Consumer
from balancer import Balancer
from confirms import Confirms
from worker import Worker


# Handles exiting when SIGTERM (sent by ^C input) is received 
# in a gracefull way. Main loop will only exit after a completed iteration
# so that every service can shut down properly. 
EXIT_PROGRAM = False
def exit_gracefully(self, signum, frame):
    global EXIT_PROGRAM
    EXIT_PROGRAM = True
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)

def balancer_consume_thread(queue):
    consumer = Consumer(
            command_queue=queue,
            connection_param="rabbitmq-frontend",
            exchange_name=os.environ["FRONTEND_EXCHANGE"],
            queue_name="frontend",
            routing_key="frontend"
        )
    consumer.run() 

def confirms_thread(workers, mutex):
    confirms = Confirms(workers=workers, mutex=mutex)
    confirms.run()

def main():
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    workers = []

    ''' Stopping worker created by docker-compose since it dosent work well
    having it in out system. This wouldent have to be done if Docker
    would implement delayed startup in docker-compose
    '''
    init_worker_container = client.containers.get("worker")
    init_worker_container.stop()

    WANTED_WORKERS = int(os.environ["NUM_WORKERS"])
    for i in range(0, WANTED_WORKERS):
        route_key = f"worker_queue_{i}"
        server_name = f"worker_{i}"
        result = client.containers.run(
            image="csc468-group3_worker",
            name=server_name,
            detach=True,
            auto_remove=True,
            #extra_hosts={"quoteserver.seng.uvic.ca":"192.168.4.2"},
            #ports={"4444":"4444"},
            network="csc468-group3_custom_network",
            environment={
                "ROUTE_KEY": route_key,
                "SERVER_NAME": server_name,
                "BACKEND_EXCHANGE": os.environ["BACKEND_EXCHANGE"],
                "CONFIRMS_EXCHANGE": os.environ["CONFIRMS_EXCHANGE"],
                "QUOTE_SERVER_PORT": os.environ["QUOTE_SERVER_PORT"],
                "MONGODB_DATABASE": os.environ["MONGODB_DATABASE"],
                "MONGODB_USERNAME": os.environ["MONGODB_USERNAME"],
                "MONGODB_PASSWORD": os.environ["MONGODB_PASSWORD"],
                "MONGODB_HOSTNAME": os.environ["MONGODB_HOSTNAME"]
            }
        )
        
        print(f"Started worker container...\n\tID: {result.id}\n\tName: {result.name}")
        sys.stdout.flush()

        workers.append(Worker(
            container_id=result.id,
            commands=[],
            route_key=route_key
        ))

    mutex = Lock()
    balancer_queue = queue.Queue()
    t_balancer_consume = Thread(target=balancer_consume_thread, args=(balancer_queue,))
    t_confirms = Thread(target=confirms_thread, args=(workers, mutex))
    t_balancer_consume.start()
    t_confirms.start()

    balancer = Balancer(workers=workers, queue=queue, mutex=mutex)
    balancer.run()

    global EXIT_PROGRAM
    while not EXIT_PROGRAM:
        if not balancer_queue.empty():
            balancer.balance(balancer_queue.get())
        
    for worker in workers:
        worker_container = client.containers.get(worker.container_id)
        worker_container.stop()

    t_balancer_consume.join()
    t_confirms.join()


if __name__ == "__main__":
    main()
