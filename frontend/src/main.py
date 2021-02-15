from flask import Flask, request, render_template

flask_app = Flask(__name__)

@flask_app.route("/")
def hell():
    return render_template("home.html")

@flask_app.route("/success",methods = ['POST', 'GET'])
def print_data():
   if request.method == 'POST':
      result = request.form
      # submit request to rabbit mq channel
#       return "Request successfully received"