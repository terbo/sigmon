#!/usr/bin/python

# tail the database
# how do you just list new upate ... ^_o

import pycouchdb as couchdb
import datetime

c = couchdb.Server()

db = c.database('sigmon')

def tail(msg, db):
	docid = msg['id']
	doc = db.get(docid)
	print("'%s','%s','%s','%s','%s','%s','%s'" % \
		(doc['mac'], doc['bssid'], doc['ssid'], doc['signal'], \
		 doc['firstseen'], doc['lastseen'], doc['vendor']))

db.changes_feed(tail)
