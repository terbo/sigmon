#!/usr/bin/python

# list unique ssids

import os
import sys
import datetime
import pycouchdb as couchdb

c = couchdb.Server()
db = c.database('sigmon')

ssids = list()

map_func = 'function(doc) { emit(doc, null); }'
results = list(db.temporary_query(map_func))


for res in results:
	doc = res['key']
	ssid = doc['ssid']
	
	if ssid not in ssids and ssid != '<ANY>':
		ssids.append(ssid)

print "Saw %d unique SSID's\n" % len(ssids)

rows, cols = os.popen('stty size', 'r').read().split()

out = ''

for ssid in sorted(ssids):
	length = len(out + ssid + '  ')
	
	if(int(length) > int(cols)):
		print out
		out = ''

	out += ssid + '  '

print ''
