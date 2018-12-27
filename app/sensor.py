#!/usr/bin/env python

from sigmon import *
from sigmon import _now

sensors = [
    {
      'name': 'sensor1',
      'status': { 'lastseen': _now(), 'connected': False},
      'role': ['sensor'],
      'location': 'rooftop',
      'longlat': { 'type': 'Point',
                    'coordinates': [ 33.329201, -111.994268 ],
                    'orientation': 'SW' },
      'info': { 'os': 'raspbian',
                'ip': '1.0.0.99',
                'brand': 'raspberry pi',
                'model': 'zero w',
                'serial': '000-xx-93920-ah',
                'desc': 'raspberry pi zero w with tp-link',
                'notes': 'none', },
      'mac':  { 'wlan0': '00:00:00:00:00:00',
                'bnep0': '00:00:00:00:00:00',
                'eth0':  '00:00:00:00:00:00' },
      'wifi': { 
                'wlan1': {
                  'chip': 'rtl8187',
                  'ant': '6dbi dipole omnl',
                  'txpower': 30,
                  'iface': 'wlan0mon',
                  'hop': True,
                },
                'wlan0': {
                  'chip': 'rtl8187',
                  'ant': '6dbi dipole omnl',
                  'txpower': 20,
                  'iface': 'mon0',
                  'hop': False,
                },
      },
      'ssh':   { 'port': 22,
                 'auth': 'key',
                 'user': 'mon',
                 'gzip': True },
    },
]

db.sensors.drop()

db.sensors.insert_many(sensors)

pp(list(db.sensors.find()))

# now check the recent probes and determine connected/lastseen?
#sigmon.col.find('time': { '$gt': now() })
