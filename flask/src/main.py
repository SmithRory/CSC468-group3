from flask import Flask, request
import sys
import socket
import time
from random import Random, randrange

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    # sleep_for = 10#randrange(5)    
    # print(f"sleeping for {sleep_for}")
    # sys.stdout.flush()

    # time.sleep(sleep_for)

    return request.form