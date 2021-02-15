# Interfaces with the 'logs' collection.
import os
import mongoengine

MONGO_URI = 'mongodb://' + os.environ['MONGODB_USERNAME'] + ':' + os.environ['MONGODB_PASSWORD'] + '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']
mongoengine.connect(host = MONGO_URI)

# assuming timestamp is in unix time, add later to check for it

# class DebugType(Document):
#     timestamp = StringField(required=True)
#     server = StringField(required=True)
#     transactionNum = IntField(required=True, min_value=0)
#     command = StringField(required=True)
#     username = StringField()
#     stockSymbol = StringField(max_length=3)
#     filename = StringField()
#     funds = DecimalField(precision=2)
#     debugMessage = StringField()
#
# class ErrorEventType(Document):
#     timestamp = StringField(required=True)
#     server = StringField(required=True)
#     transactionNum = IntField(required=True, min_value=0)
#     command = StringField(required=True)
#     username = StringField()
#     stockSymbol = StringField(max_length=3)
#     filename = StringField()
#     funds = DecimalField(precision=2)
#     errorMessage = StringField()
#
# class SystemEventType(Document):
#     timestamp = StringField(required=True)
#     server = StringField(required=True)
#     transactionNum = IntField(required=True, min_value=0)
#     command = StringField(required=True)
#     username = StringField()
#     stockSymbol = StringField(max_length=3)
#     filename = StringField()
#     funds = DecimalField(precision=2)
#
# class AccountTransactionType(Document):
#     timestamp = StringField(required=True)
#     server = StringField(required=True)
#     transactionNum = IntField(required=True, min_value=0)
#     action = StringField(required=True)
#     username = StringField(required=True)
#     funds = DecimalField(precision=2)

class QuoteServerType(mongoengine.EmbeddedDocument):
    timestamp = mongoengine.FloatField(required=True) #change to datetime if required
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    price = mongoengine.DecimalField(required=True, precision=2)
    stockSymbol = mongoengine.StringField(required=True, max_length=3)
    username = mongoengine.StringField(required=True)
    quoteServerTime = mongoengine.IntField(required=True)
    cryptokey = mongoengine.StringField(required=True)

# class UserCommandType(Document):
#     timestamp = StringField(required=True)
#     server = StringField(required=True)
#     transactionNum = IntField(required=True, min_value=0)
#     command = StringField(required=True)
#     username = StringField()
#     stockSymbol = StringField(max_length=3)
#     filename = StringField()
#     funds = DecimalField(precision=2)

class LogType(mongoengine.Document):
#     userCommand = EmbeddedDocumentListField(UserCommandType)
    quoteServer = mongoengine.EmbeddedDocumentListField(QuoteServerType)
#     accountTransaction = EmbeddedDocumentListField(AccountTransactionType)
#     systemEvent = EmbeddedDocumentListField(SystemEventType)
#     errorEvent = EmbeddedDocumentListField(ErrorEventType)
#     debugEvent = EmbeddedDocumentListField(DebugType)

# class Log(mongoengine.Document):
#     log = mongoengine.EmbeddedDocumentListField(LogType)

# class LogsTemp(mongoengine.Document):


def get_logs():
    print("In the database get_logs method")

    for log in LogType.objects:
        print("In the loop")
        print(log.to_json())

    print(LogType.objects.only('quoteServer').to_json())

#     print(QuoteServerType.objects.to_json)

    return "{}"
