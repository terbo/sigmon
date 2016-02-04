#!/usr/bin/env python
""" collide your workarounds with audobon inertia dance """


import sys
import pymongo
import datetime
from logging import info 

import bz2

mongo = pymongo.MongoClient(host='dv8')

db = mongo.sigmon

ssid_db = db.ssids
probe_db = db.probes
client_db = db.clients
ap_db = db.aps
vendor_db = db.vendors

SR = lambda x: x.lstrip().rstrip()[1:-1]
i = 0

def sync(data):
  client = client_db.insert_one( {'mac': data['mac'],
                                  'ssid': data['ssid'],
                                  'drone': data['drone'],
                                  'time': datetime.datetime.utcfromtimestamp(float(data['time'])),
                                  'signal': data['signal']
                                 })

def get_client(line):
  line = line.split('\n')[0].split(',')
  from_drone = SR(line.pop(0))
  probe_time = SR(line.pop(0))
  mac = SR(line.pop(0))
  signal = SR(line.pop(0))
  ssid = SR(''.join(line).decode('ascii',errors='ignore'))
  
  return { 'drone': from_drone, 'time': probe_time, 'mac': mac,
          'signal': signal, 'ssid': ssid }

for csvfile in sys.argv[1:]:
  print(csvfile)
  try:
    for line in bz2.BZ2File(csvfile,'r'):
      if len(line) < 5: continue
      sync(get_client(line))
  except Exception as e:
    print 'wtf? ', e
    pass
    # unreached
