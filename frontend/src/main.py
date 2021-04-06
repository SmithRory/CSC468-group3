from flask import Flask, render_template, redirect, url_for, request, jsonify, flash, session
from flask_bootstrap import Bootstrap
from flask_login import UserMixin, LoginManager, login_user, login_required, current_user, logout_user
from forms import LoginForm, AddForm, BuySellForm, AutoTransactionForm
from command_interface import send_command

import json

# *** CONFIGURATION start *******************************************
flask_app = Flask(__name__)
flask_app.secret_key = b'5f&e@rid5?c1>bab'

# Flask-WTF requires an encryption key
flask_app.config['SECRET_KEY'] = 'thisisarandomstringofcharacters'
Bootstrap(flask_app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(flask_app)
login_manager.login_view = 'login'

# Transaction Number
transaction_num = 1  # Global
# *** CONFIGURATION end *********************************************

# *** USER MODEL start **********************************************
my_users = {}

class User(UserMixin):
    """UserMixin provides the default implementation of the User class
    that is needed for user sessions."""

    def __init__(self, id):
        global transaction_num
        self.id = id
        # Add user to the db
        command = f"[{transaction_num}] ADD,{self.id},0.00"
        send_command(command)
# *** USER MODEL end ************************************************


@login_manager.user_loader
def load_user(user_id):
    return my_users.get(user_id)


@flask_app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        global my_users

        # Login and validate the user.
        user_id = form.username.data
        user = User(id=user_id)
        login_user(user)
        my_users.update({user_id: user})

        return redirect(url_for('homepage'))

    return render_template('login.html', form=form)


@flask_app.route('/logout')
def logout():
    my_users.pop(current_user.id)
    logout_user()
    return redirect(url_for('homepage'))


@flask_app.route("/", methods=['POST', 'GET'])
@login_required
def homepage():
    global transaction_num
    form = AddForm()

    account_summary = send_command(f"[{transaction_num}] DISPLAY_SUMMARY,{current_user.id}")
    account_summary = str(account_summary[account_summary.find('{'):account_summary.rfind('}')+1])
    account_summary = json.loads(account_summary)  # Gets just the json data

    message = None
    if 'message' in request.args:
        message = request.args.get('message')

    return render_template('index.html', form=form, message=message, account_summary=account_summary)


@flask_app.route("/buysell", methods=['POST', 'GET'])
@login_required
def buy_sell():
    global transaction_num
    form = BuySellForm()

    message = None
    if 'message' in request.args:
        message = request.args.get('message')

    return render_template('buysell.html', form=form, message=message)


@flask_app.route("/autotransaction", methods=['POST', 'GET'])
@login_required
def auto_transactions():
    global transaction_num
    form = AutoTransactionForm()

    message = None
    if 'message' in request.args:
        message = request.args.get('message')

    return render_template('autotransactions.html', form=form, message=message)


@flask_app.route("/add_api", methods=['POST'])
@login_required
def add_api():
    """ Returns the response for the given command.

    The command is given as form
    """
    global transaction_num

    # Handle the form data
    command = "ADD"
    user_id = current_user.id
    requested_command = f"[{transaction_num}] {command},{user_id}"
    transaction_num += 1

    if request.form['amount'] is not None:
        requested_command = f"{requested_command},{request.form['amount']}"

    message = send_command(requested_command)

    return redirect(url_for('homepage', message=message))


@flask_app.route("/buysell_api", methods=['POST'])
@login_required
def buysell_api():
    global transaction_num
    
    # Handle the form data.
    user_id = current_user.id
    requested_command = f"[{transaction_num}] {request.form['command']},{user_id}"
    transaction_num += 1

    stock_symbol = request.form.get('stockSymbol')
    if stock_symbol:
        requested_command = f"{requested_command},{stock_symbol}"

        amount = request.form.get('amount')
        if amount is not None:
            requested_command = f"{requested_command},{amount}"

    message = send_command(requested_command)

    return redirect(url_for('buy_sell', message=message))


@flask_app.route("/auto_api", methods=['POST'])
@login_required
def auto_api():
    global transaction_num

    # Handle the form data.
    user_id = current_user.id
    requested_command = f"[{transaction_num}] {request.form['command']},{user_id}"
    transaction_num += 1

    stock_symbol = request.form.get('stockSymbol')
    if stock_symbol:
        requested_command = f"{requested_command},{stock_symbol}"
        
        amount = request.form.get('amount')
        if amount is not None:
            requested_command = f"{requested_command},{amount}"

    message = send_command(requested_command)

    return redirect(url_for('auto_transactions', message=message))
