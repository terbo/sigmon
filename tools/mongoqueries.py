#!/usr/bin/env python
""" collide your workarounds with audobon inertia dance """
#YamI 8*8

'''
change clients to probes
populate clients every so often
populate ssids every so often
populate vendors every so often (look at snoopy wireshark git vendorfile fetch)
populate stats every so often, keep last updated, fetch that if under n-interval

'''

import sys, string, pymongo
from string import Template
from pymongo.collection import ReturnDocument
from bson.code import Code
from collections import defaultdict
import datetime as dt, time, bz2
import humanize

class percenttemplate(string.Template):
  delimiter = '%'

comma = lambda x: humanize.intcomma(x)
ntime = lambda x: humanize.naturaltime(x)

mongo = pymongo.MongoClient(host='dv8')
db = mongo.sigmon
col = db.clients

code_template = open('probemap.js').read()

t_drones = len(col.distinct('drone'))
t_ssids = len(col.distinct('ssid'))
t_clients = len(col.distinct('mac'))
t_probes = len(col.distinct('time'))

print 'Found {:,} drones which saw {:,} clients seek {:,} ssids with {:,} total probes'.format(
    t_drones, t_ssids, t_clients, t_probes)

print 'Latest clients:'

latest = col.find().skip(col.find().count()-4000)

l_clients = set()

for c in latest:
  l_clients.add(c['mac'])

print ', '.join(l_clients)

#print 'Probes:',
#for minutes in [5, 30, 60, dt.datetime.today().hour * 60, 2440]:
#  code = percenttemplate(code_template).substitute({'QUERY': '%s' % minutes,
#                                                   'OUTCOL': 'stats_%s' % minutes})
#  print db.eval(code)
  
#print '%s: %s;' % ( ntime(minutes*60), db.statistics.find() )
#print '\n\n'
print '\n'

for search in l_clients:
  print search,
  client = col.find({'mac': search})
  c_clients = set()

  for probe in client:
    #if client['time']) < _first:
    #  _first = client['time']
    #_last = client['time'])
    c_clients.add(probe['ssid'])
  
  print ', '.join(c_clients)

sys.exit(0)
  
firstseen = lastseen = 0

for probe in client:
  print drone['drone'],
  if (len(str(firstseen)) < 2) or (_first < firstseen):
    firstseen = _first
  if _last > lastseen:
    lastseen = _last
  
  totalprobes += len(drone['seen'])

print '\n\nSeen', totalprobes, 'times:', dt.datetime.fromtimestamp(float(firstseen)), dt.datetime.fromtimestamp(float(lastseen))

for search2 in l_ssids:
  print '\n\nSSID:', search2

ssid = ssid_db.find_one({'ssid': search2})

if ssid:
    for c in ssid['client']:
      mac = client.find_one({'_id':c})['mac']
      ssids = ssid_db.find({'client': c})
      print mac, [ x['ssid'] for x in ssids ]
