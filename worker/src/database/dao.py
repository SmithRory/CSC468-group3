from connect import Connect
from pymongo import MongoClient

connection = Connect.get_connection()
print("got connection")

# The pygangdb database
db = connection.pygangdb
print("got database")

# The accounts collection
db.accounts.insert_one(
    {"name": "pygang_test_user",
     "amount": 100.00,
     "stocks": {
         "ABC": 10,
         "XYZ": 15
     }})
print("insertion!")

_accounts = db.accounts.find()
print("found accounts... printing...")
for account in _accounts:
    print(account)

print("DONE!")