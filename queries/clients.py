#!/usr/bin/python

# list unique clients

import pycouchdb as couchdb
import datetime
import sys

c = couchdb.Server()
db = c.database('sigmon')

clients = dict()

map_func = 'function(doc) { emit(doc, null); }'
results = list(db.temporary_query(map_func))


for res in results:
	doc = res['key']
	mac = doc['mac']
	vendor = doc['vendor']

	if mac not in clients:
		clients[mac] = vendor

print "Saw %d unique clients's\n" % len(clients)

for mac, vendor in sorted(clients.items(), \
		cmp=lambda a,b : cmp(a, b)):
	print '%s (%s)\t' % (mac, vendor)

print ''
