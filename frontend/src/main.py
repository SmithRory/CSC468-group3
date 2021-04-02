from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField, SelectField
from wtforms.validators import DataRequired, Length, Optional

import rabbit_threads
import uuid
import queue
import threading
import time
import os
import pika

flask_app = Flask(__name__)

# *** CONFIGURATION start *******************************************

# Flask-WTF requires an encryption key
flask_app.config['SECRET_KEY'] = 'thisisarandomstringofcharacters'
Bootstrap(flask_app)

# RabbitMQ Queues
# consume_queue = queue.Queue() 
# publish_queue = queue.Queue()  
# threading.Thread(target=rabbit_threads.consumer_thread, args=(consume_queue,), daemon=True).start()
# threading.Thread(target=rabbit_threads.publisher_thread, args=(publish_queue,), daemon=True).start()

# Transaction Number
transaction_num = 1  # Global
confirms_recv = 0

# *** CONFIGURATION end *********************************************


class Form(FlaskForm):
    command = SelectField('Choose an action you want to perform', id="userCommand", validators=[DataRequired()],
                          choices=["BUY", "ADD", "QUOTE", "COMMIT_BUY", "CANCEL_BUY", "SELL", "COMMIT_SELL",
                                   "CANCEL_SELL", "SET_BUY_AMOUNT", "CANCEL_SET_BUY", "SET_BUY_TRIGGER",
                                   "SET_SELL_AMOUNT", "SET_SELL_TRIGGER", "CANCEL_SET_SELL", "DISPLAY_SUMMARY"])
    userId = StringField('What is your user id?', id="user_id", validators=[DataRequired()])
    stockSymbol = StringField('What stock do you want to trade?', id="stock_symbol",
                              validators=[Optional(), Length(min=1, max=3)])
    amount = DecimalField('Enter the amount of money you want to trade for (Please include cents)', id="funds",
                          validators=[Optional()])
    submit = SubmitField('Submit')


@flask_app.route("/", methods=['POST', 'GET'])
@flask_app.route("/<message>", methods=['POST', 'GET'])
def homepage(message=None):
    form = Form()

    if form.validate_on_submit():
        command = form.command.data
        user_id = form.userId.data
        stock_symbol = form.stockSymbol.data
        amount = form.amount.data

        print(command, user_id, stock_symbol, amount)

        return redirect(url_for('api', command=command, user_id=user_id, stock_symbol=stock_symbol, amount=amount))

    return render_template('index.html', form=form, message=message)


@flask_app.route("/api/<command>/<user_id>/")
@flask_app.route("/api/<command>/<user_id>/<stock_symbol>")
@flask_app.route("/api/<command>/<user_id>/<amount>")
@flask_app.route("/api/<command>/<user_id>/<stock_symbol>/<amount>")
def api(command, user_id, stock_symbol=None, amount=None):
    #global consume_queue
    #global publish_queue
    global transaction_num
    global confirms_recv

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host="rabbitmq")
    )
    publisher_channel = connection.channel()
    consume_channel = connection.channel()

    publisher_channel.exchange_declare(
        exchange=os.environ["FRONTEND_EXCHANGE"]
    )

    consume_channel.exchange_declare(
        exchange=os.environ["CONFIRMS_EXCHANGE"],
        exchange_type='fanout'
    )

    result = consume_channel.queue_declare(queue='')
    queue_name = result.method.queue
    consume_channel.queue_bind(
        exchange=os.environ["CONFIRMS_EXCHANGE"],
        queue=queue_name
    )

    # consume_queue = queue.Queue() 
    # publish_queue = queue.Queue()  
    # t_consume = threading.Thread(target=rabbit_threads.consumer_thread, args=(consume_queue,))
    # t_publish = threading.Thread(target=rabbit_threads.publisher_thread, args=(publish_queue,))
    # t_consume.start()
    # t_publish.start()

    requested_command = f"[{transaction_num}] {command},{user_id}"
    transaction_num += 1

    if stock_symbol:
        requested_command = f"{requested_command},{stock_symbol}"

    if amount:
        requested_command = f"{requested_command},{amount}"

    publisher_channel.basic_publish(
        exchange=os.environ["FRONTEND_EXCHANGE"],
        routing_key="frontend",
        body=requested_command,
        properties=pika.BasicProperties(),
        mandatory=True
    )

    print(f"Successfully sent command to publish queue: {requested_command}.")

    # receive confirmation from rabbitmq and store the confirmation text in message
    print("Waiting to get response from consume queue...")

    message = None
    while(message is None):
        method_frame, header_frame, message = consume_channel.basic_get(queue=queue_name)

    message = message.decode('utf-8')

    confirms_recv += 1
    print(f"Total confirms received: {confirms_recv}")
#     message = "Sentttt"
    print(f"Received response from consume queue:"
          f"\n\tOriginal Command: {requested_command}"
          f"\n\tReceived Message: {message}\n")

    #     message = requested_command # this message rn just displays the command

    # pass confirmation to form page and display the form page again
    x = url_for('homepage', message=message, _external=True)
    print(f"url is {x}")

    # t_publish.join()
    # t_consume.join()
    connection.close()

    return redirect(x)


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
