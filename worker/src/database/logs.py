# Interfaces with the 'logs' collection.
import os
from mongoengine import *

MONGO_URI = 'mongodb://' + os.environ['MONGODB_USERNAME'] + ':' + os.environ['MONGODB_PASSWORD'] + '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']
connect(host = MONGO_URI)

# assuming timestamp is in unix time, add later to check for it

class DebugType(EmbeddedDocument):
    timestamp = StringField(required=True)
    server = StringField(required=True)
    transactionNum = IntField(required=True, min_value=0)
    command = StringField(required=True)
    username = StringField()
    stockSymbol = StringField(max_length=3)
    filename = StringField()
    funds = DecimalField(precision=2)
    debugMessage = StringField()

class ErrorEventType(EmbeddedDocument):
    timestamp = StringField(required=True)
    server = StringField(required=True)
    transactionNum = IntField(required=True, min_value=0)
    command = StringField(required=True)
    username = StringField()
    stockSymbol = StringField(max_length=3)
    filename = StringField()
    funds = DecimalField(precision=2)
    errorMessage = StringField()

class SystemEventType(EmbeddedDocument):
    timestamp = StringField(required=True)
    server = StringField(required=True)
    transactionNum = IntField(required=True, min_value=0)
    command = StringField(required=True)
    username = StringField()
    stockSymbol = StringField(max_length=3)
    filename = StringField()
    funds = DecimalField(precision=2)

class AccountTransactionType(EmbeddedDocument):
    timestamp = StringField(required=True)
    server = StringField(required=True)
    transactionNum = IntField(required=True, min_value=0)
    action = StringField(required=True)
    username = StringField(required=True)
    funds = DecimalField(precision=2)

class QuoteServerType(EmbeddedDocument):
    timestamp = StringField(required=True)
    server = StringField(required=True)
    transactionNum = IntField(required=True, min_value=0)
    price = DecimalField(required=True, precision=2)
    stockSymbol = StringField(required=True, max_length=3)
    username = StringField(required=True)
    quoteServerTime = IntField(required=True)
    cryptokey = StringField(required=True)

class UserCommandType(EmbeddedDocument):
    timestamp = StringField(required=True)
    server = StringField(required=True)
    transactionNum = IntField(required=True, min_value=0)
    command = StringField(required=True)
    username = StringField()
    stockSymbol = StringField(max_length=3)
    filename = StringField()
    funds = DecimalField(precision=2)

class LogType(Document):
    userCommand = EmbeddedDocumentListField(UserCommandType)
    quoteServer = EmbeddedDocumentListField(QuoteServerType)
    accountTransaction = EmbeddedDocumentListField(AccountTransactionType)
    systemEvent = EmbeddedDocumentListField(SystemEventType)
    errorEvent = EmbeddedDocumentListField(ErrorEventType)
    debugEvent = EmbeddedDocumentListField(DebugType)

def get_logs():
    return LogType.objects.to_json()