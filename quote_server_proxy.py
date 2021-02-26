''' Most of code taken from
https://github.com/pricheal/python-client-server/blob/master/server.py

Added quote server capabilities on top of socket code
'''

import socket
import threading
import random

#Variables for holding information about connections
connections = []
total_connections = 0

stocks = {}

#Client class, new instance created for each connected client
#Each instance has the socket and address that is associated with items
#Along with an assigned ID and a name chosen by the client
class Client(threading.Thread):
    def __init__(self, socket, address, id, name, signal):
        threading.Thread.__init__(self)
        self.socket = socket
        self.address = address
        self.id = id
        self.name = name
        self.signal = signal
    
    def __str__(self):
        return str(self.id) + " " + str(self.address)
    
    def run(self):
        while self.signal:
            try:
                data = self.socket.recv(32)
                print(f"Received {data.decode('utf-8').rstrip()} from {str(self.address)}")
            except:
                print("Client " + str(self.address) + " has disconnected")
                self.signal = False
                connections.remove(self)
                break
            if data != "":
                data = data.decode("utf-8").rstrip()

                tokens = data.split(',')
                if len(tokens) != 0:
                    quote = self.get_quote(tokens[0])
                    return_string = f"{quote},{tokens[0]},{tokens[1]},abcdefghijklmnopqrstuvwxyz\n"

                    self.socket.sendall(return_string.encode("utf-8"))
                    print(f"Sent {return_string.rstrip()} to {str(self.address)}")



    def get_quote(self, stock_name):
        global stocks

        if stock_name not in stocks.keys():
            self.update_stock(stock_name=stock_name)

        return stocks.get(stock_name)

    def update_stock(self, stock_name):
        global stocks

        value = random.randrange(1, 5000)
        stocks.update({stock_name: value})
        print(f"Updated stock {stock_name} with value {value}")

        threading.Timer(
            interval=random.randrange(30, 120),
            function=self.update_stock,
            args=(stock_name,)
        ).start()


#Wait for new connections
def newConnections(socket):
    while True:
        sock, address = socket.accept()
        global total_connections
        connections.append(Client(sock, address, total_connections, "Name", True))
        connections[len(connections) - 1].start()
        print("New connection at ID " + str(connections[len(connections) - 1]))
        total_connections += 1

def main():
    host = 'localhost'
    port = 4444

    #Create new server socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(5)

    #Create new thread to wait for connections
    newConnectionsThread = threading.Thread(target = newConnections, args = (sock,))
    newConnectionsThread.start()
    
main()