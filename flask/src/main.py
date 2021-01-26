from flask import Flask, request
import sys
import socket
import time
import os
from random import Random, randrange

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        PORT = int(os.environ["BACKEND_PORT"])
        s.connect(("backend", PORT))
        s.sendall(b'Hello, world. IPC success!')
        data = s.recv(1024)

        print('Received', repr(data))
        sys.stdout.flush()
        return repr(data)

    return "Hello World"