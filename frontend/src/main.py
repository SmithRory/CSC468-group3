from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField, SelectField
from wtforms.validators import DataRequired, Length

import rabbit_threads
import uuid
import queue
import threading
import time

flask_app = Flask(__name__)

# Flask-WTF requires an encryption key
flask_app.config['SECRET_KEY'] = 'thisisarandomstringofcharacters'
Bootstrap(flask_app)

class Form(FlaskForm):
    command = SelectField('Choose an action you want to perform', id="userCommand", validators=[DataRequired()],
        choices=["BUY", "ADD", "QUOTE", "COMMIT_BUY", "CANCEL_BUY", "SELL", "COMMIT_SELL", "CANCEL_SELL", "SET_BUY_AMOUNT", "CANCEL_SET_BUY", "SET_BUY_TRIGGER", "SET_SELL_AMOUNT", "SET_SELL_TRIGGER", "CANCEL_SET_SELL", "DISPLAY_SUMMARY"])
    userId = StringField('What is your user id?', id="user_id", validators=[DataRequired()])
    stockSymbol = StringField('What stock do you want to trade?', id="stock_symbol", validators=[Length(min=1, max=3)])
    amount = DecimalField('Enter the amount of money you want to trade for (Please include cents)', id="funds", validators=[])
    submit = SubmitField('Submit')


@flask_app.route("/", methods = ['POST', 'GET'])
@flask_app.route("/<message>", methods = ['POST', 'GET'])
def homepage(message=None):
    form = Form()

    if form.is_submitted():
        command=form.command.data
        user_id=form.userId.data
        stock_symbol=form.stockSymbol.data
        amount=form.amount.data
        print(command, user_id, stock_symbol, amount)

        return redirect( url_for('api', command=command, user_id=user_id, stock_symbol=stock_symbol, amount=amount) )

    else:
        return render_template('index.html', form=form, message=message)
    return render_template('index.html', form=form, message=message)


@flask_app.route("/api/<command>/<user_id>/")
@flask_app.route("/api/<command>/<user_id>/<stock_symbol>")
@flask_app.route("/api/<command>/<user_id>/<amount>")
@flask_app.route("/api/<command>/<user_id>/<stock_symbol>/<amount>")
def api(command, user_id, stock_symbol=None, amount=None):
    transactionNum = str(uuid.uuid1())
    requested_command = "[" + transactionNum + "] " + command + "," + user_id
    if stock_symbol:
        requested_command += "," + stock_symbol
    if amount:
        requested_command += "," + amount

    print(requested_command)

    consume_queue = queue.Queue()
    publish_queue = queue.Queue()

    threading.Thread(target=rabbit_threads.consumer_thread, args=(consume_queue,)).start()
    threading.Thread(target=rabbit_threads.publisher_thread, args=(publish_queue,), daemon=True).start()
    print("Started pub/sub threads")

    # TO DO
    # send requested_command to rabbitmq
    consume_queue.put(requested_command)
    print(f"Sent command {requested_command}")

    # TO DO
    # receive confirmation from rabbitmq and store the confirmation text in message
    message = publish_queue.get()
    print(f"Recv command {requested_command}")
#     message = requested_command # this message rn just displays the command

    # pass confirmation to form page and display the form page again
    return redirect( url_for('homepage', message=message))


@flask_app.route("/stockSymbol/<command>")
def stockSymbolNeeded(command):
    commands = ["COMMIT_BUY", "CANCEL_BUY", "COMMIT_SELL", "CANCEL_SELL", "DISPLAY_SUMMARY", "ADD"]

    if command in commands:
        return jsonify({'need' : True})
    return jsonify({'need' : False})


@flask_app.route("/amount/<command>")
def amountNeeded(command):
    commands = ["ADD", "BUY", "SELL", "SET_BUY_AMOUNT", "SET_SELL_AMOUNT", "SET_BUY_TRIGGER", "SET_SELL_TRIGGER"]

    if command in commands:
        return jsonify({'need' : False})
    return jsonify({'need' : True})


'''
Create publisher and consumer in their own thread. They each have a connection
to rabbitmq only because sharing one between them would require a large rewright
of their code.

consume_queue = queue.Queue()
publish_queue = queue.Queue()

consumer = Consumer(
    queue=consume_queue,
    connection_param="rabbitmq",
    exchange_name=os.environ["CONFIRMS_EXCHANGE"],
    queue_name="frontend",
    routing_key="frontend"
)

self.publisher = Publisher(
    connection_param=self._send_address,
    exchange_name=os.environ["FRONTEND_EXCHANGE"],
    queue = publish_queue
)

Then in each thread call .run()
This is a blocking call

you can then get or put using:
consume_queue.put(data) and publish_queue.get() from the main thread

Note that both of these calls are fully thread safe and can block

'''