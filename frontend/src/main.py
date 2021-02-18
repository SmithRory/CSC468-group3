from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField, SelectField,
from wtforms.validators import DataRequired, Length

flask_app = Flask(__name__)

# Flask-WTF requires an encryption key
flask_app.config['SECRET_KEY'] = 'thisisarandomstringofcharacters'
Bootstrap(flask_app)

class NameForm(FlaskForm):
    command = SelectField('Choose an action you want to perform', id="userCommand", validators=[DataRequired()], choices=["ADD", "QUOTE", "BUY", "COMMIT_BUY", "CANCEL_BUY", "SELL", "COMMIT_SELL", "CANCEL_SELL", "SET_BUY_AMOUNT", "CANCEL_SET_BUY", "SET_BUY_TRIGGER", "SET_SELL_AMOUNT", "SET_SELL_TRIGGER", "CANCEL_SET_SELL", "DISPLAY_SUMMARY"])
    userId = StringField('What is your user id?', id="user_id", validators=[DataRequired()])
    stockSymbol = StringField('What stock do you want to trade?', id="stock_symbol", validators=[Length(min=1, max=3)])
    amount = DecimalField('Enter the amount of money you want to trade for (Please include cents)', id="funds", validators=[])
    submit = SubmitField('Submit')

@flask_app.route("/", methods = ['POST', 'GET'])
def hellx():
    form = NameForm()

    if form.is_submitted():
        result = request.form
        #TODO
        # add the result data to the rabbit queue or manager
        return render_template('user.html', result=result)
    else:
        return render_template('index.html', form=form, message="INVALIDDDD")
    return render_template('index.html', form=form, message="message")


@flask_app.route("/stockSymbol/<command>")
def stockSymbolNeeded(command):
    commands = ["COMMIT_BUY", "CANCEL_BUY", "COMMIT_SELL", "CANCEL_SELL", "DISPLAY_SUMMARY"]

    if command in commands:
        return jsonify({'need' : True})
    return jsonify({'need' : False})


@flask_app.route("/amount/<command>")
def amountNeeded(command):
    commands = ["ADD", "BUY", "SELL", "SET_BUY_AMOUNT", "SET_SELL_AMOUNT", "SET_BUY_TRIGGER", "SET_SELL_TRIGGER"]

    if command in commands:
        return jsonify({'need' : False})
    return jsonify({'need' : True})
