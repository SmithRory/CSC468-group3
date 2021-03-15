import signal
import sys
import os
import docker
from multiprocessing import Process, Queue
import threading
import time
from consumer import Consumer
from balancer import Balancer
from confirms import Confirms
from worker import Worker
from worker import RuntimeData
from worker import ThreadCommunication


# Handles exiting when SIGTERM (sent by ^C input) is received 
# in a gracefull way. Main loop will only exit after a completed iteration
# so that every service can shut down properly. 
EXIT_PROGRAM = False
def exit_gracefully(self, signum, frame):
    global EXIT_PROGRAM
    EXIT_PROGRAM = True
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)

def create_worker_thread(client, i: int, workers: list):
    route_key = f"worker_queue_{i}"
    server_name = f"worker_{i}"
    result = client.containers.run(
        image="csc468-group3_worker",
        name=server_name,
        detach=True,
        auto_remove=True,
        extra_hosts={"quoteserver.seng.uvic.ca":"192.168.4.2"},
        ports={f"{4444+i}":f"{4444+i}"},
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

    workers[i] = Worker(
        container_id=result.id,
        commands=[],
        route_key=route_key
    )


def balancer_consume_thread(communication):
    consumer = Consumer(
        communication=communication,
        buffer_limit=50000,
        connection_param="rabbitmq",
        exchange_name=os.environ["FRONTEND_EXCHANGE"],
        queue_name="frontend",
        routing_key="frontend"
    )
    consumer.run() 

def confirms_thread(workers, runtime_data):
    confirms = Confirms(
        workers=workers,
        runtime_data=runtime_data
    )
    confirms.run()

def main():
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    WANTED_WORKERS = int(os.environ["NUM_WORKERS"])
    workers = [None for _ in range(WANTED_WORKERS)]

    ''' Stopping worker created by docker-compose since it dosent work well
    having it in out system. This wouldent have to be done if Docker
    would implement delayed startup in docker-compose
    '''
    init_worker_container = client.containers.get("worker")
    init_worker_container.stop()

    t_workers = []
    for i in range(0, WANTED_WORKERS):
        t_workers.append(threading.Thread(target=create_worker_thread, args=(client, i, workers)))
    
    for w in t_workers:
        w.start()

    for w in t_workers:
        w.join()

    communication = ThreadCommunication(
        buffer=[],
        length=0,
        mutex=threading.Lock()
    )
    runtime_data = RuntimeData(
        active_commands=0,
        mutex=threading.Lock()
    )

    t_balancer_consume = threading.Thread(target=balancer_consume_thread, args=(communication,))
    t_confirms = threading.Thread(target=confirms_thread, args=(workers, runtime_data))
    t_balancer_consume.start()
    t_confirms.start()

    balancer = Balancer(
        workers=workers,
        communication=communication,
        runtime_data=runtime_data
    )
    balancer.setup()

    global EXIT_PROGRAM
    while not EXIT_PROGRAM:
        if communication.length > 0:
            balancer.balance()
        # else:
        time.sleep(2.0)

        sys.stdout.flush()
        
    for worker in workers:
        worker_container = client.containers.get(worker.container_id)
        worker_container.stop()

    t_balancer_consume.join()
    t_confirms.join()


if __name__ == "__main__":
    main()
