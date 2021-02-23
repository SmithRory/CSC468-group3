# Interfaces with the 'logs' collection.
import os
import time
import mongoengine

MONGO_URI = 'mongodb://' + os.environ['MONGODB_USERNAME'] + ':' + os.environ['MONGODB_PASSWORD'] + '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']
mongoengine.connect(host = MONGO_URI)

SERVER_NAME = os.environ["SERVER_NAME"]

# assuming timestamp is in unix time, add later to check for it

class DebugType(mongoengine.Document):
    timestamp = mongoengine.IntField(required=True)
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    command = mongoengine.StringField(required=True)
    username = mongoengine.StringField()
    stockSymbol = mongoengine.StringField(max_length=3)
    filename = mongoengine.StringField()
    funds = mongoengine.DecimalField(precision=2)
    debugMessage = mongoengine.StringField()

    def log(self, transactionNum, command, username=None, stockSymbol=None, filename=None, funds=None, debugMessage=None):
        debug_log = DebugType(timestamp=(round(time.time()*1000)), server=SERVER_NAME, transactionNum=transactionNum, command=command, username=username, stockSymbol=stockSymbol, filename=filename, funds=funds, debugMessage=debugMessage).save()


class ErrorEventType(mongoengine.Document):
    timestamp = mongoengine.IntField(required=True)
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    command = mongoengine.StringField(required=True)
    username = mongoengine.StringField()
    stockSymbol = mongoengine.StringField(max_length=3)
    filename = mongoengine.StringField()
    funds = mongoengine.DecimalField(precision=2)
    errorMessage = mongoengine.StringField()

    def log(self, transactionNum, command, username=None, stockSymbol=None, filename=None, funds=None, errorMessage=None):
        err_log = ErrorEventType(timestamp=(round(time.time()*1000)), server=SERVER_NAME, transactionNum=transactionNum, command=command, username=username, stockSymbol=stockSymbol, filename=filename, funds=funds, errorMessage=errorMessage).save()

class SystemEventType(mongoengine.Document):
    timestamp = mongoengine.IntField(required=True)
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    command = mongoengine.StringField(required=True)
    username = mongoengine.StringField()
    stockSymbol = mongoengine.StringField(max_length=3)
    filename = mongoengine.StringField()
    funds = mongoengine.DecimalField(precision=2)

    def log(self, transactionNum, command, username=None, stockSymbol=None, filename=None, funds=None):
        sys_evnt_log = SystemEventType(timestamp=(round(time.time()*1000)), server=SERVER_NAME, transactionNum=transactionNum, command=command, username=username, stockSymbol=stockSymbol, filename=filename, funds=funds).save()

class AccountTransactionType(mongoengine.Document):
    timestamp = mongoengine.IntField(required=True)
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    action = mongoengine.StringField(required=True)
    username = mongoengine.StringField(required=True)
    funds = mongoengine.DecimalField(required=True, precision=2)

    def log(self, transactionNum, action, username, funds):
        transaction_log = AccountTransactionType(timestamp=(round(time.time()*1000)), server=SERVER_NAME, transactionNum=transactionNum, action=action, username=username, funds=funds).save()

class QuoteServerType(mongoengine.Document):
    timestamp = mongoengine.IntField(required=True)
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    price = mongoengine.DecimalField(required=True, precision=2)
    stockSymbol = mongoengine.StringField(required=True, max_length=3)
    username = mongoengine.StringField(required=True)
    quoteServerTime = mongoengine.IntField(required=True)
    cryptokey = mongoengine.StringField(required=True)

    def log(self, transactionNum, price, stockSymbol, username, quoteServerTime, cryptokey):
        quote_log = QuoteServerType(timestamp=(round(time.time()*1000)), server=SERVER_NAME, transactionNum=transactionNum, price=price, stockSymbol=stockSymbol, username=username, quoteServerTime=quoteServerTime, cryptokey=cryptokey).save()


class UserCommandType(mongoengine.Document):
    timestamp = mongoengine.IntField(required=True)
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    command = mongoengine.StringField(required=True)
    username = mongoengine.StringField()
    stockSymbol = mongoengine.StringField(max_length=3)
    filename = mongoengine.StringField()
    funds = mongoengine.DecimalField(precision=2)

    def log(self, transactionNum, command, username=None, stockSymbol=None, filename=None, funds=None):
        command_log = UserCommandType(timestamp=(round(time.time()*1000)), server=SERVER_NAME, transactionNum=transactionNum, command=command, username=username, stockSymbol=stockSymbol, filename=filename, funds=funds).save()

def get_logs():

    json_data = "{ \"userCommand\": " + UserCommandType.objects.exclude("id").to_json() + ","
    json_data += "\"quoteServer\" : " + QuoteServerType.objects.exclude("id").to_json() + ","
    json_data += "\"accountTransaction\" : " + AccountTransactionType.objects.exclude("id").to_json() + ","
    json_data += "\"systemEvent\" : " + SystemEventType.objects.exclude("id").to_json() + ","
    json_data += "\"errorEvent\" : " + ErrorEventType.objects.exclude("id").to_json() + ","
    json_data += "\"debugEvent\" : " + DebugType.objects.exclude("id").to_json()
    json_data += "}"
    
    return json_data
