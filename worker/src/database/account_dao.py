from connect import Connect
from pymongo import MongoClient

# The accounts collection
'''db.accounts.insert_one(
    {"user_id": "pygang_test_user",
     "account": 1000.00,
     "available": 825.00,
     "stocks": [
         { "symbol": "ABC", "amount" : 10 },
         { "symbol": "XYZ", "amount" : 15 }
     ],
     "auto_buy": [
        { "symbol": "ABC", "amount": 5, "trigger": 10.00 },
        { "symbol": "FOO", "amount": 15, "trigger": 5.00 }
     ], 
     "auto_sell": [
         { "symbol": "XYZ", "amount": 12, "trigger" : 15.00 }
     ]})'''

def create_user(user_id):
    # Check the user hasn't been created
    user = db.accounts.find_one({"user_id": user_id})
    print(user)

# Checks if the user exists. Returns None 
#def user_exists(user_id):


def get_users():
    _accounts = db.accounts.find()
    for account in _accounts:
        print(account)

connection = Connect.get_connection()
db = connection.pygangdb
create_user('test user')