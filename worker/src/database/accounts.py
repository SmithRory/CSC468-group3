import os
from mongoengine import *

MONGO_URI = 'mongodb://' + os.environ['MONGODB_USERNAME'] + ':' + os.environ['MONGODB_PASSWORD'] + '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']
connect(host = MONGO_URI)

class Stocks(EmbeddedDocument):
    symbol = StringField(required=True, max_length=3)
    amount = IntField(required=True)

class AutoTransaction(EmbeddedDocument):
    symbol = StringField(required=True, max_length=3)
    amount = IntField(required=True)
    trigger = DecimalField(default=0.00, precision=2)

class Accounts(Document):
    user_id = StringField(required=True, unique=True)
    account = DecimalField(default=0.00, precision=2)
    available = DecimalField(default=0.00, precision=2)
    stocks = EmbeddedDocumentListField(Stocks, default=[])
    auto_buy = EmbeddedDocumentListField(AutoTransaction, default=[])
    auto_sell = EmbeddedDocumentListField(AutoTransaction, default=[])

def get_users():
    print('Users:')
    for user in Accounts.objects:
        print(user.to_json())


