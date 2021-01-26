from flask import Flask, request, render_template
# import sys
# import socket
# import time
# from random import Random, randrange

flask_app = Flask(__name__)

'''@flask_app.route("/")
def home():
    # sleep_for = 10#randrange(5)
    # print(f"sleeping for {sleep_for}")
    # sys.stdout.flush()
    # time.sleep(sleep_for)
    return request.form'''

@flask_app.route("/")
def hell():
    return render_template("home.html")

'''@app.route('/success',methods = ['POST', 'GET'])
def print_data():
   if request.method == 'POST':
      result = request.form
      return render_template("result_data.html",result = result)'''