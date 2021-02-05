import os
from pymongo import MongoClient

class Connect(object):
    @staticmethod
    def get_connection():
        mongo_uri = 'mongodb://' + os.environ['MONGODB_USERNAME'] + ':' + os.environ['MONGODB_PASSWORD'] + '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']
        return MongoClient(mongo_uri)