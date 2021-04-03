from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DecimalField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    submit = SubmitField('Login')


class AddForm(FlaskForm):
    amount = DecimalField('Deposit amount', validators=[DataRequired()])
    submit = SubmitField('Submit')


class BuySellForm(FlaskForm):
    command = SelectField('Command', id="userCommand", validators=[DataRequired()],
                          choices=["QUOTE", "BUY", "COMMIT_BUY", "CANCEL_BUY", "SELL", "COMMIT_SELL",
                                   "CANCEL_SELL"])
    stockSymbol = StringField('Stock Symbol', id="stock_symbol",
                              validators=[DataRequired(), Length(min=1, max=3)])
    amount = DecimalField('Amount', id="funds", validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Submit')


class AutoTransactionForm(FlaskForm):
    command = SelectField('Command', id="userCommand", validators=[DataRequired()],
                          choices=["QUOTE", "SET_BUY_AMOUNT", "CANCEL_SET_BUY", "SET_BUY_TRIGGER",
                                   "SET_SELL_AMOUNT", "SET_SELL_TRIGGER", "CANCEL_SET_SELL"])
    stockSymbol = StringField('Stock Symbol', id="stock_symbol",
                              validators=[DataRequired(), Length(min=1, max=3)])
    amount = DecimalField('Amount', id="funds", validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Submit')
