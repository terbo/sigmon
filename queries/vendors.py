#!/usr/bin/python

# list unique vendors

import pycouchdb as couchdb
import datetime
import sys

c = couchdb.Server()
db = c.database('sigmon')

vendors = list()

map_func = 'function(doc) { emit(doc, null); }'
results = list(db.temporary_query(map_func))

for res in results:
	doc = res['key']
	vendor = doc['vendor']

	if vendor not in vendors:
		vendors.append(vendor)

print "Saw %d unique vendors's\n" % len(vendors)

col = 0
for vendor in vendors:
	print vendor
