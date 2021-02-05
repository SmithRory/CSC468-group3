import os
#from pymongo import MongoClient
from mongoengine import connect

# This currently isn't used. Should be able to eventually be deleted.
class Connect(object):
    @staticmethod
    def get_connection():
        mongo_uri = 'mongodb://' + os.environ['MONGODB_USERNAME'] + ':' + os.environ['MONGODB_PASSWORD'] + '@' + os.environ['MONGODB_HOSTNAME'] + ':27017/' + os.environ['MONGODB_DATABASE']
        connect(host = mongo_uri)