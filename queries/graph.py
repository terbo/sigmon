#!/usr/bin/python

# show a daily probe graph

import pycouchdb as couchdb
import datetime as dt, time
import time
c = couchdb.Server()

db = c.database('sigmon')

# get the epoch time of 12am this morning
t = dt.datetime.today()
to = time.mktime(dt.datetime.timetuple(dt.datetime(int(t.strftime('%Y')),int(t.strftime('%m')),int(t.strftime('%d')))))
tm = to + 86400

map_func = 'function(doc) { if(doc.lastseen > %s && doc.lastseen < %s) { emit(doc, null);} }' % (to, tm)
results = list(db.temporary_query(map_func))

probes = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
totalprobes = 0

# take to and add an hour and get probes and rinse
for d in results:
	p = d['key']
	
	last = int(p['lastseen'][:10])
	
	if(last > to and last < (to + 3600)):
		probes[0] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 2))):
		probes[1] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 3))):
		probes[2] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 4))):
		probes[3] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 5))):
		probes[4] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 6))):
		probes[5] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 7))):
		probes[6] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 8))):
		probes[7] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 9))):
		probes[8] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 10))):
		probes[9] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 11))):
		probes[10] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 12))):
		probes[11] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 13))):
		probes[12] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 14))):
		probes[13] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 15))):
		probes[14] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 16))):
		probes[15] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 17))):
		probes[16] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 18))):
		probes[17] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 19))):
		probes[18] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 20))):
		probes[19] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 21))):
		probes[20] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 22))):
		probes[21] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 23))):
		probes[22] += 1
		totalprobes += 1
	elif(last > to and last < (to + (3600 * 24))):
		probes[23] += 1
		totalprobes += 1
	
	
	
	
	
	
'''
	for time in range(0,23):
		check = to + ((time + 1) * 3600)
		
		print '%s < %s' % (check, p['lastseen'])
		if(p['lastseen'] < check):
			print '.',
'''


print 'Saw a total of %d probes on %s\n' % (totalprobes, dt.datetime.today())

for time in range(0,23):
	if(probes[time]):
		p = probes[time] / 50

		print '%d %d | %s \n' % (probes[time], time, p*'X')
