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

def balancer_publish_thread(workers, queue, mutex):
    balancer = Balancer(workers=workers, queue=queue, mutex=mutex)
    balancer.run()

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
        result = client.containers.run(
            image="csc468-group3_worker",
            detach=True,
            auto_remove=True,
            network="csc468-group3_custom_network",
            environment={
                "ROUTE_KEY": route_key,
                "BACKEND_EXCHANGE": os.environ["BACKEND_EXCHANGE"],
                "CONFIRMS_EXCHANGE": os.environ["CONFIRMS_EXCHANGE"],
                "QUOTE_SERVER_PORT": os.environ["QUOTE_SERVER_PORT"],
                "MONGODB_DATABASE": os.environ["MONGODB_DATABASE"],
                "MONGODB_USERNAME": os.environ["MONGODB_USERNAME"],
                "MONGODB_PASSWORD": os.environ["MONGODB_PASSWORD"],
                "MONGODB_HOSTNAME": os.environ["MONGODB_HOSTNAME"]
            }
        )
        
        print(f"Started worker container {result.id}")
        sys.stdout.flush()

        workers.append(Worker(
            container_id=result.id,
            commands=[],
            route_key=route_key
        ))

    mutex = Lock()
    balancer_queue = queue.Queue()
    t_balancer_consume = Thread(target=balancer_consume_thread, args=(balancer_queue,))
    t_balancer_publish = Thread(target=balancer_publish_thread, args=(workers, balancer_queue, mutex))
    t_confirms = Thread(target=confirms_thread, args=(workers, mutex))
    t_balancer_consume.start()
    t_balancer_publish.start()
    t_confirms.start()

    global EXIT_PROGRAM
    while not EXIT_PROGRAM:
        time.sleep(1) 
        sys.stdout.flush()         
        
    for worker in workers:
        worker_container = client.containers.get(worker.container_id)
        worker_container.stop()

    t_balancer_consume.join()
    t_balancer_publish.join()
    t_confirms.join()


if __name__ == "__main__":
    main()
