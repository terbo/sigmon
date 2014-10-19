#!/usr/bin/python

# tail the database

import os
import sys
import time
import signal
import datetime
import pycouchdb as couchdb

c = couchdb.Server()
db = c.database('sigmon')
uptime = datetime.datetime.now()

probes=0

def sigint(signal, frame):
  print('Seen %s probes since %s.' % ( probes, uptime ) )
  print('Press Ctrl-\ to exit.')

signal.signal(signal.SIGINT, sigint)

def sigmon_tail(msg, db):
	docid = msg['id']
	
	doc = db.get(docid)
	
	global probes
	probes += 1

	print("'%s','%s','%s','%s','%s','%s','%s'" % (doc['lastseen'], \
			doc['firstseen'], doc['mac'], doc['bssid'], doc['ssid'], doc['signal'], doc['vendor']))
	
while True:
	db.changes_feed(sigmon_tail, descending='true')
