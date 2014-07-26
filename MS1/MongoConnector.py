__author__ = 'Nimrod Ben-Em'
from pymongo import MongoClient
import logging


class MongoConnector:
    def __init__(self):
        print 'Init MongoConnector Class'
        self.mongo_client = None
        self.db = None
        self.db_collection = None
        self.connection_status = False

    def init_connection(self, ip, port):
        # connect to DB server
        self.mongo_client = MongoClient(ip, port)
        if self.mongo_client is None:
            print 'Failed to connect DB Server at:%s@%d' % (ip, port)
            return False

        #Authenticate to Server
        #auth_succeeded = mongo_client.clouDNS.authenticate(user, password)
        #if auth_succeeded is False:
        #    return False

        # Select ClouDNS DB
        self.db = self.mongo_client['ClouDNS']
        if self.db is None:
            print 'Failed to get DB ClouDNS'
            return False

        # Select DNS Queries Collection
        self.db_collection = self.db['ClouDNS_Queries']
        if self.db_collection is None:
            print 'Failed to get DB Collection ClouDNS_Queries'
            return False

        self.connection_status = True
        return self.connection_status

    def init_connection_with_auth(self, ip, port, user, password):
        # connect to DB server
        self.mongo_client = MongoClient(ip, port)
        if self.mongo_client is None:
            print 'Failed to connect DB Server at:%s@%d' % (ip, port)
            return False

        #Authenticate to Server
        auth_succeeded = self.mongo_client.clouDNS.authenticate(user, password)
        if auth_succeeded is False:
            logging.error('Authentication Failed...')
            return False

        # Select ClouDNS DB
        self.db = self.mongo_client['ClouDNS']
        if self.db is None:
            print 'Failed to get DB ClouDNS'
            return False

        # Select DNS Queries Collection
        self.db_collection = self.db['ClouDNS_Queries']
        if self.db_collection is None:
            print 'Failed to get DB Collection ClouDNS_Queries'
            return False

        self.connection_status = True
        return self.connection_status

    def insert_dns_query(self, dns_query):
        print 'DNS To Insert: %s' % dns_query
        query_id = self.db_collection.insert(dns_query)
        return query_id

    def is_connected(self):
        return self.connection_status
