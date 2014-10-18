#!/usr/bin/python

# search for clients that search for a specific ssid

import pycouchdb as couchdb
import datetime
import sys

c = couchdb.Server()

db = c.database('sigmon')

ssid = sys.argv[1]

map_func = 'function(doc) { if(doc.ssid == "' + ssid + '") emit(doc, null); }'
results = list(db.temporary_query(map_func))

macs = dict()

for res in results:
	mac = res['key']['mac']
	vendor = res['key']['vendor']
	if(mac not in macs):
		macs[mac] = vendor

print 'Clients that searched for SSID %s: \n' % ssid

for mac, vendor in macs.items():
	print '%s: %s' % (mac, vendor)
