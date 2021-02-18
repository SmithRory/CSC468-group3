# Interfaces with the 'logs' collection.
import os
import mongoengine

MONGO_URI = 'mongodb://' + os.environ['MONGODB_USERNAME'] + ':' + os.environ['MONGODB_PASSWORD'] + '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']
mongoengine.connect(host = MONGO_URI)

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

    def log(self, timestamp, server, transactionNum, command, username=None, stockSymbol=None, filename=None, funds=None, debugMessage=None):
#                             # Get all the logs.
#                             logs = LogType.objects.first()
#                             # Create the new log.
                            debug_log = DebugType(timestamp=timestamp, server=server, transactionNum=transactionNum, command=command, username=username, stockSymbol=stockSymbol, filename=filename, funds=funds, debugMessage=debugMessage).save()
#                             # Append the new command log.
#                             logs.debugEvent.append(debug_log)
#                             logs.save()

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

    def log(self, timestamp, server, transactionNum, command, username=None, stockSymbol=None, filename=None, funds=None, errorMessage=None):
#                         # Get all the logs.
#                         logs = LogType.objects.first()
#                         # Create the new log.
                        err_log = ErrorEventType(timestamp=timestamp, server=server, transactionNum=transactionNum, command=command, username=username, stockSymbol=stockSymbol, filename=filename, funds=funds, errorMessage=errorMessage).save()
#                         # Append the new command log.
#                         logs.errorEvent.append(err_log)
#                         logs.save()

class SystemEventType(mongoengine.Document):
    timestamp = mongoengine.IntField(required=True)
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    command = mongoengine.StringField(required=True)
    username = mongoengine.StringField()
    stockSymbol = mongoengine.StringField(max_length=3)
    filename = mongoengine.StringField()
    funds = mongoengine.DecimalField(precision=2)

    def log(self, timestamp, server, transactionNum, command, username=None, stockSymbol=None, filename=None, funds=None):
#                     # Get all the logs.
#                     logs = LogType.objects.first()
#                     # Create the new log.
                    sys_evnt_log = SystemEventType(timestamp=timestamp, server=server, transactionNum=transactionNum, command=command, username=username, stockSymbol=stockSymbol, filename=filename, funds=funds).save()
#                     # Append the new command log.
#                     logs.systemEvent.append(sys_evnt_log)
#                     logs.save()

class AccountTransactionType(mongoengine.Document):
    timestamp = mongoengine.IntField(required=True)
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    action = mongoengine.StringField(required=True)
    username = mongoengine.StringField(required=True)
    funds = mongoengine.DecimalField(required=True, precision=2)

    def log(self, timestamp, server, transactionNum, action, username, funds):
#                 # Get all the logs.
#                 logs = LogType.objects.first()
#                 # Create the new log.
                transaction_log = AccountTransactionType(timestamp=timestamp, server=server, transactionNum=transactionNum, action=action, username=username, funds=funds).save()
#                 # Append the new quote log.
#                 logs.accountTransaction.append(transaction_log)
#                 logs.save()

class QuoteServerType(mongoengine.Document):
    timestamp = mongoengine.IntField(required=True) #change to datetime if required
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    price = mongoengine.DecimalField(required=True, precision=2)
    stockSymbol = mongoengine.StringField(required=True, max_length=3)
    username = mongoengine.StringField(required=True)
    quoteServerTime = mongoengine.IntField(required=True)
    cryptokey = mongoengine.StringField(required=True)

    def log(self, timestamp, server, transactionNum, price, stockSymbol, username, quoteServerTime, cryptokey):
#         # Get all the logs.
#         logs = LogType.objects.first()
#         # Create the new log.
        quote_log = QuoteServerType(timestamp=timestamp, server=server, transactionNum=transactionNum, price=price, stockSymbol=stockSymbol, username=username, quoteServerTime=quoteServerTime, cryptokey=cryptokey).save()
#         # Append the new quote log.
#         logs.quoteServer.append(quote_log)
#         logs.save()

class UserCommandType(mongoengine.Document):
    timestamp = mongoengine.IntField(required=True)
    server = mongoengine.StringField(required=True)
    transactionNum = mongoengine.IntField(required=True, min_value=0)
    command = mongoengine.StringField(required=True)
    username = mongoengine.StringField()
    stockSymbol = mongoengine.StringField(max_length=3)
    filename = mongoengine.StringField()
    funds = mongoengine.DecimalField(precision=2)

    def log(self, timestamp, server, transactionNum, command, username=None, stockSymbol=None, filename=None, funds=None):
#                 # Get all the logs.
#                 logs = LogType.objects.first()
#                 # Create the new log.
                command_log = UserCommandType(timestamp=timestamp, server=server, transactionNum=transactionNum, command=command, username=username, stockSymbol=stockSymbol, filename=filename, funds=funds).save()
#                 # Append the new command log.
#                 logs.userCommand.append(command_log)
#                 logs.save()

# class LogType(mongoengine.Document):
#
#     userCommand = mongoengine.EmbeddedDocumentListField(UserCommandType)
#     quoteServer = mongoengine.EmbeddedDocumentListField(QuoteServerType)
#     accountTransaction = mongoengine.EmbeddedDocumentListField(AccountTransactionType)
#     systemEvent = mongoengine.EmbeddedDocumentListField(SystemEventType)
#     errorEvent = mongoengine.EmbeddedDocumentListField(ErrorEventType)
#     debugEvent = mongoengine.EmbeddedDocumentListField(DebugType)


def get_logs():
    json_data = "{ \"userCommand\": " + UserCommandType.objects.exclude("id").to_json() + ","
    json_data += "\"quoteServer\" : " + QuoteServerType.objects.exclude("id").to_json() + ","
    json_data += "\"accountTransaction\" : " + AccountTransactionType.objects.exclude("id").to_json() + ","
    json_data += "\"systemEvent\" : " + SystemEventType.objects.exclude("id").to_json() + ","
    json_data += "\"errorEvent\" : " + ErrorEventType.objects.exclude("id").to_json() + ","
    json_data += "\"debugEvent\" : " + DebugType.objects.exclude("id").to_json()
    json_data += "}"
#     print(json_data)
    return json_data
