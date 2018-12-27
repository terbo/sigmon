#!/usr/bin/python

from __future__ import absolute_import
from __future__ import division

""" sigmon.py v0.9z - (c) cbt 10/01/14 """

VERSION         = (0, 9, '9z')
__version__     = '.'.join((str(_) for _ in VERSION))
__author__      = 'CB Terry https://github.com/terbo'
__url__         = 'https://github.com/terbo/sigmon'

# read code, comment code, write code
# write code, write code, read code
# write code, comment code, comment code
# comment code, comment code, read code

import sys, os, re, platform
import time, resource
from glob import glob
from datetime import timedelta, datetime as dt
from pprint import pprint as pp, pformat as pf
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import Terminal256Formatter
def ppc(obj):
  print highlight(pf(obj), PythonLexer(), Terminal256Formatter())

import pytz, random, coloredlogs, logging, humanize
import dateutil.parser, bson

from logging import error, debug, info
from collections import defaultdict
import manuf, tqdm
from paho.mqtt import client as mqttclient
import binascii

#from netaddr import EUI

#logging.basicConfig(format=' %(asctime)s : %(levelname)s : %(message)s',level=logging.DEBUG)
coloredlogs.install()
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(funcName)s %(threadName)s(%(lineno)d) -%(levelno)s: %(message)s')

import pymongo
from pymongo import MongoClient as M
from pymongo.errors import BulkWriteError 
  
from geopy.distance import vincenty
from geopy.point import Point as gPoint
from shapely.geometry import Polygon as sPoly, Point as sPoint
from geojson import Polygon as gPoly

import pcapy, impacket
from impacket import ImpactDecoder

TZ=pytz.timezone(os.environ.get('SIGMON_TZ', 'US/Pacific'))
UTC=pytz.timezone('UTC')

SIGMON_ROOT = os.environ.get('SIGMON_ROOT', '/sigmon')
SIGMON_DATA = os.environ.get('SIGMON_DATA', '/data/sigmon')
SIGMON_PCAP = SIGMON_DATA + '/app/static/captures/incoming'

SIGMON_MONGO_URL = os.environ.get('SIGMON_MONGO_URL', 'localhost')
SIGMON_MQTT_URL = SIGMON_MONGO_URL
SIGMON_MQTT_PORT = 1883
SIGMON_MQTT_KEEPALIVE = 60

WORKER_SLEEP_TIME = {'session': 5, 'device': 1, 'stats': 4}

LOW_PROBES = int(os.environ.get('SIGMON_LOW_PROBES', 50))
HIGH_PROBES = int(os.environ.get('SIGMON_HIGH_PROBES', 800))

PROXIMITY_LOW_RSSI = int(os.environ.get('SIGMON_PROXIMITY_LOW_RSSI', -39))
PROXIMITY_HIGH_RSSI = int(os.environ.get('SIGMON_PROXIMITY_HIGH_RSSI', -70))

OVERVIEW_MINUTES = int(os.environ.get('SIGMON_OVERVIEW_MINUTES', 5))
SESSION_LENGTH = int(os.environ.get('SIGMON_SESSION_LENGTH', 15))
SENSOR_CHECK_TIME = int(os.environ.get('SIGMON_SENSOR_CHECK_TIME', 3))

TX_POWER = -26 # this will be calculated automatically from iwconfig details

RTD = ImpactDecoder.RadioTapDecoder()
watch_list = {}

own_ssids = {'Any'}

#####
##  Database helpers
#####

# going into the eve schema setup
def first_setup():
  collections = list(db.collection_names())

  # link time and mac by newest probe first
  # what about hashing the macs?
  # remove non-alpha, lowercase
  # all mac access is through a filter sub
  # that removes, adds, anonymizes, or prettyfies standard mac

  if 'probes' not in collections: db.create_collection('probes')
  db.probes.drop_indexes()
  db.probes.create_index('_created',sparse=True, background=True)
  db.probes.create_index('time',sparse=True, background=True)
  db.probes.create_index('mac',sparse=True, background=True)
  db.probes.create_index([('time',pymongo.ASCENDING) ,('mac',pymongo.TEXT)],sparse=True, background=True)

  if 'probes.hourly' not in collections: db.create_collection('probes.hourly')
  db.probes.hourly.drop_indexes()
  db.probes.hourly.create_index('hour',sparse=True, background=True)
  db.probes.hourly.create_index('mac',sparse=True, background=True)
  db.probes.hourly.create_index([('hour',pymongo.ASCENDING) ,('mac',pymongo.TEXT)],sparse=True, background=True)
  
  if 'probes.daily' not in collections: db.create_collection('probes.daily')
  db.probes.daily.drop_indexes()
  db.probes.daily.create_index('day',sparse=True, background=True)
  db.probes.daily.create_index('mac',sparse=True, background=True)
  db.probes.daily.create_index([('day',pymongo.ASCENDING) ,('mac',pymongo.TEXT)],sparse=True, background=True)

  if 'sensors' not in collections: db.create_collection('sensors')
  
  if 'ssids' not in collections: db.create_collection('ssids')
  
  if 'vendors' not in collections: db.create_collection('vendors')
  
  if 'aps' not in collections: db.create_collection('aps')
  db.aps.drop_indexes()
  db.aps.create_index('mac',sparse=True, background=True)
  db.aps.create_index([('ssid',pymongo.TEXT),('mac',pymongo.TEXT)],sparse=True, background=True)
  
  if 'bts' not in collections: db.create_collection('bts')

  if 'sessions' not in collections: db.create_collection('sessions')
  db.sessions.drop_indexes()
  db.sessions.create_index([('enter',pymongo.ASCENDING),('mac',pymongo.TEXT)],sparse=True, background=True)
  
  if 'settings' not in collections: db.create_collection('settings')
  
  if 'logs.jobs' not in collections: db.create_collection('logs.jobs')
  if 'logs.sensors' not in collections: db.create_collection('logs.sensors')
  if 'logs.web' not in collections: db.create_collection('logs.webs')
  
  if 'devices' not in collections: db.create_collection('devices')
  db.devices.drop_indexes()
  db.devices.create_index('tags', sparse=True, background=True)
  db.devices.create_index([('lastseen',pymongo.ASCENDING),('mac',pymongo.TEXT)], sparse=True, background=True)
  
  # also, import template databases
  # make indexes
  # check versions
  # check files
  # etc
  pass

def totalprobes():
  return db.probes.find().count()

def totalstats():
  return {
     'aps': commify(db.aps.find().count()),
     'bts': commify(db.bts.find().count()),
     'probes': commify(totalprobes()),
      'ssids': commify(db.ssids.find().count()),
    'devices': commify(db.devices.find().count()),
    'vendors': commify(db.vendors.find().count()),
   'sessions': commify(db.sessions.find().count())
  }

def probes_per_month():
  per = {}
  per['week'] = int(db.probes.find({'_created': {'$gt': _now()-_week(1)}}).count() / 60 / 24 / 7)
  per['month'] = int(db.probes.find({'_created': {'$gt': _now()-_month(1)}}).count() / 60 / 24 / 7 / 4)
  
  return per

def probes_per_sensor(start='',stop=1,sensor=False):
  if not start:
    start = _now()
    
  match = {
    '$match': {
    '_created': { '$gt': start.replace(minute=0,second=0) - _hours(2),
              '$lt': _now()
            }
    }
  }

  if sensor:
    match.update({'sensor': sensor})

  group = { '$group': {
    '_id': '$sensor',
    'probes': {'$sum': 1},
    'maxrssi': {'$min': '$rssi'},
    'minrssi': {'$max': '$rssi'},
    'avgrssi': {'$avg': '$rssi'},
  }}

  probes_pipeline = [ match, group ]
  
  res = list(db.probes.aggregate(probes_pipeline))
  
  sensors = {}

  for sensor in res:
    name = sensor['_id']
    sensors[name] = sensor
    sensors[name]['avgrssi'] = int(round(sensor['avgrssi']))

  return sensors

def js(func,args=False):
  if func in lsjs():
    return eval('db.system_js.%s()' % func)

def lsjs():
  return sorted(db.system_js.list())

def lsdb(pretty=True):
  dblist={}
  if pretty:
      for x in db.collection_names(): dblist[x] = commify(eval('db.%s.find().count()' % x))
  else:
      for x in db.collection_names(): dblist[x] = eval('db.%s.find().count()' % x)
  if pretty:
    return pp(dblist)
  else:
    return dblist

def lsdbs():
  return js('dbstats')

def dbdump(dbname,rlimit=500):
  res = eval("db.%s.find().limit(%s).sort([('_id',-1)])" % (dbname, rlimit))
  return res

#####
##  Date/time
#####

def _minute(x=1):
  return timedelta(seconds=60 * int(x))
def _minutes(x=1):
  return _minute(x)


def _hour(x=1):
  return timedelta(seconds=60 * 60 * int(x))
def _hours(x=1):
  return _hour(x)


def _day(x=1):
  return timedelta(seconds=60 * 60 * 24 * int(x))
def _days(x=1):
  return _day(x)


def _week(x=1):
  return timedelta(seconds=60 * 60 * 24 * 7 * int(x))
def _weeks(x=1):
  return _week(x)


def _month(x=1):
  return timedelta(seconds=60 * 60 * 24 * 7 * 4 * int(x))
def _months(x=1):
  return _months(x)


def _now(tz=TZ):
    return dt.now(tz)

#####
##  Tracking
####

def trackadd(host,loc):
  mac = owndevs(name=host).keys()[0]
  debug('adding %s - %s - %s' % (mac, host, loc))
  ll = {'type': 'Point','coordinates': [ loc.split(',') ] }
  track = trackmac(mac)
  db.fingerprints.insert_one({'mac': mac, 'location': ll, 'track': track, 'time': dt.utcnow() })

# search fingerprint db for last 15 minutes of tracking
def trackview(mac):
  #debug('searching for %s' % mac)
  fingerprint = db.fingerprints.find({'mac':mac},{'_id':False}).limit(1).sort([('time',-1)])
  
  if fingerprint.count():
    fingerprint = list(fingerprint)
    debug('Found %d records' % len(fingerprint))
    #debug(fingerprint)
    
    return { 'mac': fingerprint[0]['mac'], 'time': fingerprint[0]['time'], 'location': fingerprint[0]['location'],
             'track': fingerprint[0]['track'] }

def trackmac(mac, mins=1, limit=1):
  info('looking up %s' % mac)
  res = []
  sensors = dictify(list(db.sensors.find({},{'_id':False})),'name')
  
  for sensor in sensors: # ugly, but dunno if it works the same unchained?
    #debug(sensor)
    out = col.find({ 'mac':    mac,  'sensor': sensor, 
                     '_created': { '$gt': _now() - _minutes(mins) } },
                   { 'mac':    True, '_created':  True,
                     'rssi':   True, 'seq':   True,
                     'sensor': True, '_id': False}).sort([('_created',-1),('seq',-1)]).limit(limit) # how to pass these ...
    if out.count():
      out = out[0]
      debug(out['_created'])
    
      res.append( {'mac':    out['mac'],
                   'time':   out['_created'],
                   'rssi':   out['rssi'],
                   'sensor': sensor,
                   'seq':    out['seq'],
                  } )
  return res

def obsmac(mac):
  newmac = re.sub(r'[A-Za-z0-9][A-Za-z0-9]:[A-Za-z0-9][A-ZA-z0-9]$','00:0%d' % random.randint(0,5),mac)
  return newmac

####
##  Queries
####

def owndevs(mac=None, name=None):
  query = {'tags': 'owned'}
  
  if mac:  query.update({'mac': mac})
  if name: query.update({'name': name})
  
  return dictify(list(db.devices.find(query,{'_id':False})),'mac')

def aplist(mins=15,start=''):
    if not start:
        start = _now()
    # aww screwy.

    out = db.aps.find({'_created':{'$gt': _now() - _minutes(mins)} },{'_id': False})
    return list(out)

def regulars():
    return list(db.devices.find({'sessions': {'$gt': 2}, 'tags': { '$all':  ['regular','session']}},{'_id':False}))

def overview(mins=OVERVIEW_MINUTES, start='', getaps=True, getbts=False, getsessions=True, getdata=True, getprobes=True, tagfilter=[], obscure_macs=False):
  # it was caching the function definition..
  if not start:
    start = _now()
    
  current_probes = int()

  mins = _minutes(mins)
  current_ssids = set()
  current_vendors = set()
  
  tags = set()
  probes = [] 
  totals = {}
  datapkts = []
  sessions = []
 
  owned_devices = owndevs().keys()

  overview_pipeline = [
      { '$match':
        {'_created': # using this as we cant rely on 'time' being updated
          { '$gt': (start - mins),
            '$lt': (start + mins) }
        }
      },
      { '$group': {
                    '_id': '$mac',
                    '_created': { '$max': '$_created' },
                    'ts': { '$max': '$time' },
                    'pktime': { '$max': '$pktime' },
                    'ssids': { '$addToSet': '$ssid' },
                    'count': { '$sum': 1 },
                    'lastrssi': { '$last': '$rssi' },
                    'maxrssi': { '$min': '$rssi' },
                    'minrssi': { '$max': '$rssi' }, 
                    'firstseen': { '$min': '$_created' }, 
                    'sensors': { '$addToSet': '$sensor' },
                  }
      },
      {'$project': {
                    '_id': '$_id',
                    'ts': '$time',
                    'time': '$_created',
                    'pktime': '$pktime',
                    'maxrssi': '$maxrssi',
                    'minrssi': '$minrssi',
                    'lastrssi': '$lastrssi',
                    'sensors': '$sensors',
                    'probes': { '$sum': '$count'},
                    'ssids': '$ssids',
                   }
      }, 
      { '$sort':  { '_id': -1 } }
  ]

  bt_pipeline = [
    { '$match':
      {'_created':
        {'$gt': (start - mins) }
      }
    },
    {'$group':
      {'_id': '$mac',
       'count': { '$sum': 1 },
       'firstseen': {'$min': '$time' },
       'lastseen': {'$max': '$time' },
       'maxrssi': { '$min': '$rssi'},
       'minrssi': {'$max': '$rssi'}, 
       'lastrssi': { '$last': '$time'}
      }
    },
    {'$project':
      { 'devclass': '$devclass',
            'name': '$name',
        'seen':'$lastseen',
        'lastseen':'$lastseen',
           'count': '$count',
         'maxrssi': '$maxrssi',
         'minrssi': '$minrssi',
        'lastrssi': '$lastrssi'
      }
    }
  ]
  
  session_start = start - _minutes(start.minute) + _hour(1)
  
  aps = []
  if getaps == True:
    debug('[overview]   ---   aps')
    for ap in db.aps.aggregate(overview_pipeline):
      ap.pop('probes')
      ap.update({'vendor': vendor_oui(ap['_id'])})
      aps.append(ap)
  

  if getsessions == True:
    debug('[overview]   ---   sessions')
    for x in xrange(1, 1 * 60,SESSION_LENGTH):
      s = db.sessions.find({'enter': {'$gt': start - _minutes(x), '$lt': start } },{'_id':False})
      sessions.append({'start': start.strftime('%F %T'),
                     'end': (start - _minutes(x)).strftime('%T'),
                     'count':s.count(), 'sessions': list(s) })
      session_start -= _minutes(x)

  bts = [] 
  if getbts == True:
    debug('[overview]   ---   bts')
    for bt in db.bt.aggregate(bt_pipeline):
      bt.update({'vendor': vendor_oui(bt['_id'])})
      bts.append(bt)

 # dgraph = []
  
  if getdata == True:
    datapkts = list(db.datapkts.find({'_created': {'$gt': start - _minutes(x), '$lt': start } },
                                     {'_id':False}))

  if getprobes == True:
    debug('[overview]   ---   get devices')
    devices = dictify(db.devices.find({'lastseen': {'$gte': start - mins }}),'mac')
    debug('[overview]   ---   exit devices')

    for pkt in col.aggregate(overview_pipeline):
      #debug('[overview]   ---   new pkt')
      pkt.update({'time': pkt['time'].astimezone(TZ)})
      
      if not devices.has_key(pkt['_id']):
        if len(tagfilter) and 'new' not in tagfilter:
          continue
        
        pkt.update({'firstseen': pkt['time'].strftime('%F %T')})
        pkt.update({'vendor': vendor_oui(pkt['_id'])})
        pkt.update({'tags': ['new'] })
        pkt.update({'sessioncount': 0 })
      else:
        if len(tagfilter) and tagfilter not in device['tags']:
          continue
        
        device = devices[pkt['_id']]
        current_vendors.add(device['vendor'])
   
        pkt.update({'allssids': device['ssids']})
        pkt.update({'firstseen': device['firstseen'].strftime('%F %T')})
        pkt.update({'firstseens': device['firstseen'].strftime('%s')})
        
        pkt.update({'tags': device['tags']})
        pkt.update({'sessioncount': db.sessions.find({'mac':pkt['_id']}).count() })
        pkt.update({'vendor': device['vendor']})
      
      ## notifications - soon to be in another class

      for ssid in pkt['ssids']:
        if ssid in own_ssids and pkt['_id'] not in owned_devices:
          notice('access point','device %s is searching for SSID %s (%s)' % \
            (pkt['_id'],ssid, ','.join(pkt['sensors'])))
          pkt['tags'].append('alert')
          pkt['tags'].append('wifinet')
   
        current_ssids.add(ssid)

      current_probes += pkt['probes']
      
      if pkt['_id'] in watch_list.values():
          notice('watch-list','device %s is within %s signal (%s)' % \
            ( pkt['_id'], pkt['minrssi'], ','.join(pkt['sensors'])))
          pkt['tags'].append('alert')
          pkt['tags'].append('watchlist')

      if int(pkt['minrssi']) >= int(PROXIMITY_LOW_RSSI):
        if pkt['_id'] not in owndevs().keys():
          notice('proximity','device %s is within %s signal (%s)' % \
            ( pkt['_id'], pkt['minrssi'], ','.join(pkt['sensors'])))
          pkt['tags'].append('alert')
          pkt['tags'].append('proximity')
      
      for s in pkt['sensors']:
          pkt['tags'].append(s)
      
      for tag in pkt['tags']:
        tags.add(tag)
      
      lastseen = (_now() - pkt['time']).total_seconds() # timedelta
      pkt.update({'lastseens': pkt['time'].strftime('%s') })
      pkt.update({'lastseen': deltafy(lastseen) })

      if obscure_macs:
        pkt.update({'mac': obsmac(pkt['_id']) })
      else: 
        pkt.update({'mac': pkt['_id'] })
     
      #pkt.update({'macpretty': pkt['mac']})
      #pkt.update({'mac': pkt['mac'].replace(':','_') })
      
      #if 'alert' in pkt['tags']:
      #  if 'wifinet' in pkt['tags']:
      #    os.system('/data/sigmon/notice.sh')
      
      probes.append(pkt)
   
  #dgraph = [ { 'mac':vendmac(x['mac'],x['vendor']),
  #               'tags':x['tags'],
  #               'probes':x['probes'],
  #               'sensors':x['sensors'],
  #               'lastrssi':x['lastrssi'],
  #               'sessions':x['sessioncount'],
  #               'ssids':x['ssids'] } for x in probes ]
      
  totals = totalstats()
  debug('[overview]   ---   active sensors')
  sensors = active_sensors()
  current_probes = commify(current_probes)

  debug('[overview]   ---   exit')
  return { 'range': [start, (start - mins)], 
           'aps': aps,
           'datapkts': datapkts,
           'bts': bts,
           'totals': totals,
           'probes': probes,
           'currentprobes': current_probes,
           'vendors': list(current_vendors),
           'ssids': list(current_ssids),
           'sensors': sensors, 
           'sessions': sessions,
           #'dgraph': dgraph,
           'tags': list(tags) }

def trmac(omac):
  pass
  # m/[A-Z]{6}[_-:] remove chars lowercase return
  # m/[^_-:] add chars return lc

def vendmac(m,v):
  return re.sub(r'^([A-Za-z0-9][A-Za-z0-9]:){4}','%s_' % v,m)

def whosaw(q, period='', since=5):
  data = []
  
  if not period:
    period = _now()
  
  whosaw_pipeline = [
    { '$match': {
        'mac': q,
        '_created': {'$gt': period - _minutes(since)},
      }
    },
    { '$group': {
        '_id': '$sensor',
        'mac': { '$addToSet': '$mac' },
        'ssids': { '$addToSet': '$ssid' },
        'minrssi':  { '$max': '$rssi' },
        'avgrssi':   { '$avg': '$rssi' },
        'maxrssi':  { '$min': '$rssi' },
        'firstseq':  { '$min': '$seq' },
        'lastseq':  { '$last': '$seq' },
        'firstseen': { '$first': '$_created' },
        'lastseen': { '$last': '$_created' },
        'lastrssi': { '$last': '$rssi' },

      }
    },
    { '$project': {
       'ssids': '$ssids' ,
       'avgrssi': '$avgrssi',
       'minrssi': '$minrssi',
       'maxrssi': '$maxrssi',
       'lastseq': '$lastseq',
       'firstseen': '$firstseen',
       'lastseen': '$lastseen',
       'lastrssi': '$lastrssi',
      }
    }
  ]
  
  #pp(whosaw_pipeline)
  
  ret = col.aggregate(whosaw_pipeline)

  for p in ret:
      p['totalprobes'] = col.find({'mac':q},{'_id':False}).count()
      p['firstseen'] = p['firstseen'].astimezone(TZ)
      p['lastseen'] = p['lastseen'].astimezone(TZ)
      data.append(p)

  return {'now':_now(), 'data': data }

# return the given macs vendor if available
# sent a mac first searches vendor database for oui, then full text
#def vendor_oui(mac):
#  oui = EUI(mac)
#  try:
#    vendoroui  = oui.info['OUI']['oui']
#    vendorname = oui.info['OUI']['org']
#  except:
#    return 'Unknown'
  
def vendor_oui(mac):
  if not mac:
    return 
  
  try:
    res = macparser.get_all(mac)
    if(res[0]):
        vendor_short = res[0]
    else:
        vendor_short = 'Unknown'
 
    if(res[1]):
        vendor_long = res[1]
    else:
        vendor_long = 'Unknown'
    
    vendor_oui = ''
    #debug('mac: %s / %s / %s / %s' % ( mac, res[0], res[1], res[2] ))
    
    #vendor_oui = '%x' % (macparser._get_mac_int(macparser._strip_mac(mac)) >> res[2])
  except Exception as e:
    print('%s: %s' % ( mac, e ))
    return 'Unknown'

  if(vendor_short == 'Unknown'):
      search = db.vendors.find_one({ 'long': vendor_long }, {'_id':False})
  elif (vendor_long == 'Unknown'):
      search = db.vendors.find_one({ 'name': vendor_short}, {'_id':False})
  else:
      search = db.vendors.find_one({'$or': [ 
                       { 'long': vendor_long },
                       { 'name': vendor_short} ] }, {'_id':False})
  if not search:
    db.vendors.update_one({'name': vendor_short,
                           'oui': vendor_oui },
                          {'$push': {
                           'long': vendor_long,
                           'macs': mac}
                          },
                            upsert=True)

  #info('Found OUI for MAC: %s / %s' % ( vendor_short, vendor_long ) ) 
  return vendor_short

def lookup(q):
  if re.match(r'(?:[0-9a-fA-F]:?){12}',q):
    info = list(db.devices.find({'mac': q},{'_id':False}))
    try:
      info[0]['firstseen'] = info[0]['firstseen'].astimezone(TZ)
      info[0]['lastseen'] = info[0]['lastseen'].astimezone(TZ)
    except:
      pass
    
    sessions = get_sessions(q,limit=100)
    probes = list(col.find({'mac':q, '_created': {'$gt': _now()-_week(1) }},
                           {'_id':False,'time':False,'_etag':False,
                            'mac':False,'version':False,'_updated':False,
                            'ptype':False,'channel':False,'stats':False,
                            'dst_mac':False,'frame':False}))
                     #.sort([('_created',-1)]))
    
    dates = {}
    for p in probes:
      p.update({'_created': p['_created'].astimezone(TZ)})
      ts = p['_created'].replace(second=0)
      key = ts.strftime('%Y-%m-%d %H:%M')
      if not dates.has_key(key):
        dates[key] = 0
      dates[key] += 1
    probes = [['x'],['dates']]
    for d in sorted(dates):
        probes[0].append(d)
        probes[1].append(dates[d])
    
    totalprobes = col.find({'mac':q},{'_id':False}).count()

    return { q: { 'sessions': sessions, 'probes': probes, 'totalprobes': totalprobes, 'info': info } }
  else:
    return list(col.aggregate([{ '$match': { 'ssid': q } },
                            { '$group': { '_id': '$mac' , 'count': { '$sum': 1} } },
                            { '$sort':  { 'count': -1 } } ]))

# return last num probes
def taildb(num=5, since=False, stream=False, mac=False):
    query = {}
    '''if since and type(since) == float:
      res = col.find({
        '_created': {
          '$gt':dt.fromtimestamp(since).replace(tzinfo=TZ)
        }
      }).sort([('_id',-1)]).limit(50)
    else: '''
    if(mac):
        query = {'mac': mac}

    res = col.find(query,{'_id':False}).sort([('_id',-1)]).limit(num)
    return list(res)

#####
##  Sessions
####

def session_worker(mac=False,start='',hours=1,session_length=SESSION_LENGTH,do_update=True):
  found = 0
  if not start:
    start = lastrun('session')
    
  if mac:
    bymac = [mac]
  else:
    bymac = db.probes.hourly.find({'hour': {'$gt': start - _hours(hours) }}).distinct('mac')

  logjob('session','start',(start,hours))
  ret = ''

  session_length = timedelta(minutes=session_length).total_seconds()
  sessions = {}
  bulk_sessions = db.sessions.initialize_unordered_bulk_op()

  for mac in tqdm.tqdm(bymac):
    sess = db.sessions.find({'mac': mac, 'enter': { '$gt': start - _hours(hours) }})
    if sess.count():
      continue
      #return sess
    
    np = list(db.probes.hourly.find({'mac':mac, 'hour': {
                                                  '$gt': start - _hours(hours) }
                                    }).sort([('hour',1)]))
    totalprobes = 0
    
    if len(np) and np[0].has_key('hour'):
      # say what now?
      firstseen = np[0]['hour'] + timedelta(minutes=int(sorted(np[0]['probes'].keys())[0]))
    else:
      debug('no firstseen in list? %s %s' % ( mac, len(np) ))
      continue

    sessions[mac] = [{'enter': firstseen}]

    for h in xrange(len(np)):
        p = np[h]

        probes = 0
        probehash = p['probes']
        lastseen = firstseen
        minutes = list(sorted(probehash.keys()))
        
        for i in xrange(len(minutes)):
          minute = minutes[i]
          probes += probehash[minute]
          ts = p['hour'] + timedelta(minutes=int(minute))
            
          if (ts - lastseen).total_seconds() > session_length:
            if sessions[mac][-1].has_key('exit'):
              sessions[mac].append({'enter': ts})
          elif (len(np) > h + 1) and (np[h+1]['hour'] + timedelta(minutes=int(sorted(np[h+1]['probes'].keys())[0])) - ts).total_seconds() <  session_length:
            continue
          elif len(sessions) and sessions[mac][-1].has_key('enter') and \
            (lastseen - ts).total_seconds() > session_length:
            sessions[mac][-1]['exit'] = ts

          lastseen = ts
        totalprobes += probes

    if totalprobes < 50:
      continue
    
    for s in tqdm.tqdm(sessions[mac]):
      found += 1
      if not s.has_key('enter'):
        continue
      if not s.has_key('exit'): s['exit'] = False # open session
      
      bulk_sessions.insert({'mac':mac, 'enter': s['enter'], 'exit': s['exit'] })

  if do_update and found:
    try:
      ret = bulk_sessions.execute()
    except BulkWriteError as bwe:
      debug('error bulk write: %s' % bwe.message)
  
  logjob('session','end',ret)
  
  if ret:
    return ret

def get_sessions(mac,limit=50):
  ret = []
  #debug('enter %d: ' % limit)
  session = db.sessions.find({'mac':mac},{'_id':False}).limit(limit).sort([('_id',-1)])
   
  if session.count() < 1:
    return { 'response': False }
  
  #debug('session')

  sessions = []

  for s in session:
    if s.has_key('exit'):
      if type(s['exit']) != bool and type(s['enter']) != bool:
        s.update({'exit': s['exit'].astimezone(TZ)})
        s.update({'enter': s['exit'].astimezone(TZ)})
        s['duration'] = deltafy((s['exit'] - s['enter']))
        s.update({'exit': s['exit'].strftime('%F %T') })
        s.update({'enter': s['enter'].strftime('%F %T') })
        sessions.append(s) 
  
  ret.append({'sessioncount': session.count()})
  ret.append({'sessions': list(sessions)})

  return ret

#####
##  Sensor / SSH
####

def active_sensors(sensor_check_time=SENSOR_CHECK_TIME, check_active=True, return_all=False):
  sensor_pipeline = [
    { '$match':
        {'_created':
          { '$gt': _now() - _minutes(sensor_check_time) }
        }
    },
    { '$group': {
       '_id': '$sensor',
        'time': { '$max': '$_created' }
      }
    }
   ]
 
  active = dictify(db.probes.aggregate(sensor_pipeline), '_id' )
   
  sensors = dictify(db.sensors.find({},{'_id':False,}), 'name')

  pps = probes_per_sensor()

  for sensor in pps.keys():
    sensors[sensor].update({'status':pps[sensor]})

  if(check_active):
    for sensor in sensors:
      #info('Testing sensor %s' % sensor)
      if sensor in active:
        lastseen = active[sensor]['time']
        #info('Last seen: %s' % lastseen)
        active[sensor] = sensors[sensor]
        active[sensor]['status']['lastseen'] = lastseen
        active[sensor]['status']['connected'] = True

        db.sensors.update_one({'name': sensor},
                                {'$set': {
                                'status.lastseen': lastseen,
                                'status.connected': True,
                                }
                              })
      else:
        #info('Setting connected = False')
        db.sensors.update_one({'name': sensor}, 
                                {'$set': {
                                  'status.connected': False
                                  }
                              })
        #del sensors[sensor]
  info('Active sensors: %s' % active.keys())
  
  if return_all:
    return sensors
  else:
    return active

####
##  Notifications
####

def get_notices(access='admin',concern='',read=False):
  query = {'read': read}
  
  if concern:
    query.update({'concern': concern})
  
  notices = db.messages.find(query,{'_id':False})
  
  if notices.count():
    info('notifications: [%s]' % notices.count())
    #info('%s: %s' % (notices.count(), list(notices)))
    return list(notices)

def notice(concern, message=False, markread=False):
  last_concern_time = db.messages.find_one({'concern':concern,
                                           'read': False})
  if last_concern_time and markread:
    # now only saved in sessions() data
    db.messages.update_one({'_id':last_concern_time['_id']},{'$set': {'read': True}})
    return True
  
  elif last_concern_time:
    # silently ignore ..
    return

  elif concern and message:
    #debug('%s [%s]' % ( message, concern ))
    mqtt.publish('/sigmon/notice/%s' % concern, message)
    
    db.messages.insert_one({'concern':concern,
                            'message':message,
                            'time':_now(),'read':False})
  else:
    error('No concern or message')

####
##  Workers
####

def device_worker(mac=False,start=False,minutes=1,days=False):
  if not start:
    start = lastrun('device') - _minutes(minutes+(SESSION_LENGTH*4))

  minutes = _minutes(minutes)

  logjob('device','start','start=%s,days=%s,minutes=%s' % (start,days,minutes))
  debug('fetching queue/ssids')
  
  queue = db.probes.hourly.find({'hour': {'$gte': start - minutes } } )
  
  if not queue.count():
    logjob('device','end','my work here is done: %s' % queue.count())
    return

  ret = modified = modified_ssids = 0
  
  ssidlist = dictify(list(db.ssids.find({},{'_id':False})), 'ssid')
  bulk_ssids = db.ssids.initialize_unordered_bulk_op()

  probes_pipeline = [
    { '$match': { '_created': {'$gte': start - minutes } } },
    { '$group': {
       '_id': '$mac',
       'maxrssi': {'$min': '$rssi' },
       'minrssi': {'$max': '$rssi' },
       'seenby': {'$addToSet': '$sensor'},
       'ssids': {'$addToSet': '$ssid'},
       'lastseen': {'$max': '$_created' },
       'totalprobes': { '$sum': 1 }
      }
    }
  ]
  
  debug('fetching probes/aggregation')
  
  probes = dictify(list(db.probes.aggregate(probes_pipeline)),'_id')

  debug('first/last')
  
  firstlast_pipeline = [
    { '$match': {
          'mac': { 
              '$in': probes.keys()
                  }
                }
    },
    { '$group': {
        '_id':  '$mac',
        'firstseen': {'$min': '$time'},
        'lastseen': {'$max': '$time'}
      }
    }
  ] 

  firstlast = dictify(list(db.probes.aggregate(firstlast_pipeline)),'_id')
 
  bulk_devices = db.devices.initialize_unordered_bulk_op()
  
  totalprobes = {}

  devices = defaultdict(defaultdict)

  debug('found %s devices to inspect' % queue.count())
  
  for dev in tqdm.tqdm(queue):
    mac = dev['mac']
    if mac not in probes:
      debug('%s is missing from probes' % mac)
      continue

    tags = []

    for tm in dev['probes']:
      hour = (dev['hour'] + timedelta(minutes=int(tm))).strftime('%s')
      devices[mac][hour] = dev['probes'][tm]

    if probes[mac]['totalprobes'] < LOW_PROBES:
      tags.append('lowprobes')
    elif probes[mac]['totalprobes'] < HIGH_PROBES:
      tags.append('medprobes')
    else:
      tags.append('highprobes')

    if probes[mac]['minrssi'] > PROXIMITY_LOW_RSSI:
      tags.append('close')
    # medium? avg?
    if probes[mac]['maxrssi'] < PROXIMITY_HIGH_RSSI:
      tags.append('far')
    
    sessioncount = db.sessions.find({'mac': mac}).count()

    if sessioncount:
      tags.append('session')
    
    # seen more than thrice in two hours
    # what is this??
    if len(devices[mac].keys()) > 1:
      tags.append('repeat')
    elif len(devices[mac].keys()) <= 3:
      tags.append('regular')
    
    vendor = vendor_oui(mac)
    
    if vendor == 'Unknown':
      tags.append('unknown')
    else:
      tags.append('oui')

    # delete broadcast ssid
    for ssid in probes[mac]['ssids']:
      if not len(ssid):
        del probes[mac]['ssids']

    # looking for more than 3, or no, ssids?
    if probes[mac].has_key('ssids'):
      if len(probes[mac]['ssids']) >= 2:
        tags.append('ssid')
      if len(probes[mac]['ssids']) >= 4:
        tags.append('loud')
      elif len(probes[mac]['ssids']) <= 1:
        tags.append('quiet')
    else:
      probes[mac]['ssids'] = ['']
    
    for ssid in probes[mac]['ssids']:
      if len(ssid) and (ssid not in ssidlist.keys() or mac not in ssidlist[ssid].values()): 
        modified_ssids += 1
        bulk_ssids.find({ 'ssid': ssid}).upsert().update({ '$addToSet': { 'mac': mac }})
    
    if mac in owndevs().keys():
      tags.append('owned')

    if type(firstlast[mac]['firstseen']) in [float,int]:
      firstlast[mac]['firstseen'] = dt.fromtimestamp(int(firstlast[mac]['firstseen'])).replace(tzinfo=TZ)
    elif type(firstlast[mac]['firstseen']) == unicode:
      firstlast[mac].update({'firstseen': dateutil.parser.parse(firstlast[mac]['firstseen']).replace(tzinfo=TZ) })
    
    modified += 1

    bulk_devices.find({'mac': mac}).upsert().update(
                 {'$addToSet': {
                        'alltags': {'$each': tags },
                        'ssids': {'$each': probes[mac]['ssids'] } },
                  '$set': {
                    'mac': mac,
                    'vendor': vendor,
                    'firstseen': firstlast[mac]['firstseen'],
                    'lastseen': probes[mac]['lastseen'],
                    'sensors': probes[mac]['seenby'],
                    'tags': tags,
                    'sessions': sessioncount
                    } } )

  debug('submitting...')
  
  try:
    if modified_ssids: ssid_ret = bulk_ssids.execute()
    if modified: ret = bulk_devices.execute()
  except BulkWriteError as bwe:
    debug('error bulk write: %s' % bwe.message)

  logjob('device','end','return=%s' % ret)

  return {'result': True,
          'modified_devices': modified,
          'modified_ssids': modified_ssids}
  
def stats_worker(limit=2000):
  logjob('stats','start')
  queue = db.probes.find({'stats': {'$exists': False}}).limit(limit).sort([('_id',-1)])
  modified = 0
  results = {}

  if not queue.count():
     logjob('stats','no packets found')
     return

  bulk_probes = bulk_daily = bulk_hourly = False
 
  pkday = pkhour = 0
  hourfield = minutefield = ''

  to_process = queue.count()
  
  logjob('stats','found probes',to_process)
  
  bulk_probes = db.probes.initialize_unordered_bulk_op()
  bulk_hourly = db.probes.hourly.initialize_unordered_bulk_op()
  bulk_daily  = db.probes.daily.initialize_unordered_bulk_op()
  
  for probe in tqdm.tqdm(queue):
    mac = probe['mac']

    #debug('Original time: %s' % probe['time'])
    if type(probe['time']) in [float,int]:
      probe.update({'time': dt.fromtimestamp(float(probe['time'])).replace(tzinfo=TZ) })
    elif type(probe['time']) == unicode:
      probe.update({'time': dateutil.parser.parse(probe['time']).replace(tzinfo=TZ) })
      
    #debug('New time: %s' % probe['time'])
    
    pkday = probe['time']
  
    pkday = pkday.replace(hour=0,minute=0,second=0,microsecond=0)
    #pkday -= _hours(pkday.hour)
    #pkday -= _minutes(pkday.minute)
    #pkday -= timedelta(seconds=pkday.second)
    #pkday -= timedelta(microseconds=pkday.microsecond)
  
    pkhour = pkday + _hours(probe['time'].hour)
    
    #debug('PKday/Hour: %s / %s' % (pkday, pkhour))

    hourfield = 'probes.%s' % str(probe['time'].hour)
    minutefield = 'probes.%s' % str(probe['time'].minute)

    #debug('hour/minute: %s / %s' % (hourfield, minutefield ))
    
    bulk_hourly.find({'mac': mac,
                     'hour': pkhour}).upsert().update({'$inc':
                                                      { minutefield: 1 } })

    bulk_daily.find({ 'mac': mac,
                      'day': pkday}).upsert().update({'$inc':
                                                     { hourfield: 1 } })

    bulk_probes.find({'_id': probe['_id']}).update({'$set': {'stats': True ,
                                                              'time': probe['time'] }})

    modified += 1

  if modified:
    try:
      results['daily'] = bulk_daily.execute()
      results['hourly'] = bulk_hourly.execute()
      results['probes'] = bulk_probes.execute()
    except BulkWriteError as bwe:
      debug('error bulk write: %s' % bwe.message)

  logjob('stats','end','%s modified' % modified)
  
  return

# executed from workers.sh
def run_worker(worker):
  while True:
    debug('executing %s_worker' % worker)
    eval('%s_worker()' % worker)
    
    debug('sleeping %s minutes .' % WORKER_SLEEP_TIME[worker])
    time.sleep(60 * WORKER_SLEEP_TIME[worker])


def logjob(worker,action,args=False):
  debug('worker: %s, action: %s -- %s' % ( worker, action, args ))
  db.logs.jobs.insert_one({'worker':worker,'action':action,
                      'args':args,'time':_now()})

def lastrun(worker):
  last_job = db.logs.jobs.find({'worker':worker,'action':'end'},{'_id':False,'time':True}).sort([('_id',-1)]).limit(1)
  if last_job.count():
    return last_job[0]['time']
  else:
    return _now() - _minutes(WORKER_SLEEP_TIME[worker] - (SESSION_LENGTH * 2))

def weightedrssi(mac):
  seenby = whosaw(mac)['data']
  avg_last_rssi = 0.0 
  rssis = {}
  meters = {}
  total = 0 
  probes = {}
  weights = {}

  for sensor in seenby:
      probes[sensor['_id']] = sensor['totalprobes']
      rssis[sensor['_id']] = sensor['lastrssi']
      total += sensor['totalprobes']

  for sensor in probes:
    weights[sensor] = (total / probes[sensor]) / len(seenby)
    
  
  for sensor in rssis:
    avg_last_rssi += rssis[sensor] * weights[sensor]
  
  for sensor in seenby:
    sensor = sensor['_id']
    try:
      meters[sensor] = 10 ** (( 20 - rssis[sensor] ) / 20)
      #meters[sensor] = (10 ** ((((avg_last_rssi / len(seenby)) * (1/1.2)) + 38.45) / -15.08))
    except:
      meters[sensor] = 0

  try:
    weightedRssi = (avg_last_rssi / len(seenby))
  except:
    weightedRssi = 0
  
  return { 'seen_by': seenby, 'weightedRssi': weightedRssi, 'meters': meters }

##### 
##  Graphing
#####

# display collection stats since 12am
def graphdata(day='',month='',year='',time='',hours=24):
  if time:
    day = time.day
    month = time.month
    year = time.year
  else:
    if not day:
      day = _now().day
    if not month:
      month = _now().month
    if not year:
      year = _now().year

  start = _now().replace(day=day,month=month,year=year) - _hours(_now().hour);
  end = start + _hours(hours)
  
  timespan = {'$gt': start, '$lt': end }

  probes_count = 0
  daily_graph = defaultdict(int)
  hourly_graph = defaultdict(int)
  
  devices = db.devices.find({'lastseen': timespan } )
  sessions = db.sessions.find({'enter': timespan } )
  session_count = sessions.count()
  
  sessions = list(sessions)
  
  sessions_hourly = defaultdict(int)
  
  for session in sessions:
    if session['mac'] in owndevs().keys():
      continue
      
    enter = session['enter']
    enter_h = enter.hour
    enter_m = enter.minute
    ts = enter.strftime('%d/%m/%Y %H:')
    
    if enter_m < 30:
      ts += '00:00'
    else:
      ts += '30:00'
    
    sessions_hourly[ts] += 200
  
  tmp = sessions_hourly
  sessions_hourly = []

  for dev in tmp:
    sessions_hourly.append(tmp[dev])

  new_devices = db.devices.find({'firstseen': timespan } )
  new_devices_hourly = defaultdict(int)

  for dev in new_devices:
    firstseen = dev['firstseen']
    hour = firstseen.hour
    minute = firstseen.minute
    ts = firstseen.strftime('%d/%m/%Y %H:')
    
    if minute < 30:
      ts += '00:00'
    else:
      ts += '30:00'
    
    new_devices_hourly[ts] += 100

  tmp = new_devices_hourly
  new_devices_hourly = []

  for dev in tmp:
    new_devices_hourly.append(tmp[dev])

  daily_probes = db.probes.daily.find({'day': timespan })
  hourly_probes = db.probes.hourly.find({'hour': timespan })
  
  for i in daily_probes:
    for hour in i['probes'].keys():
      if i['mac'] in owndevs().keys():
        continue
      ts = i['day'].replace(hour=int(hour)).astimezone(TZ).strftime('%d/%m/%Y %H:%M:%S')
      probes_count += i['probes'][hour]
      daily_graph[ts] += i['probes'][hour]

  for i in hourly_probes:
    for minute in i['probes']:
      if minute < 30:
        mins = 00
      else:
        mins = 30
      ts = i['hour'].replace(minute=int(mins)).astimezone(TZ).strftime('%d/%m/%Y %H:%M:%S')
      hourly_graph[ts] += i['probes'][minute]

  seen_vendors=defaultdict(int)
  
  totalvendors = 0
  
  for i in devices:
    #if i['mac'] in owndevs().keys():
    #  continue
    vendor = i['vendor']
    #if vendor == 'Unknown':
    #  continue
    totalvendors += 1
    seen_vendors[vendor] += 1
  vendors = []
  vendorout = {}
  other = 0

  for vendor in sorted(seen_vendors):
    vendorc = int(seen_vendors[vendor])
    if 100 * (float(vendorc) / float(totalvendors)) < 1:
      other += int(vendorc)
    else:
      vendors.append(['%s (%d)' % (vendor,vendorc), vendorc])

  vendors.append(['Other %s' % other, other])

  for v in vendors:
      #debug(v)
      vendorout[v[0]] = v

  u_graph = []
  p_graph = []
  d_graph = []
  h_graph = []

  for hour in daily_graph:
    u_graph.append(hour)
    p_graph.append(daily_graph[hour])
  
  for hour in hourly_graph:
    d_graph.append(hour)
    h_graph.append(hourly_graph[hour])


  return { 'start': '%s - %d hours' % (start.strftime('%F %T'), hours),
           'device_count': devices.count(),
           'session_count': session_count,
           'probe_count': probes_count,
           'seen_vendors': vendorout,
           'sessions_hourly': sessions_hourly,
           'new_devs_hourly': new_devices_hourly,
           'daily_graph': u_graph,
           'daily_probes': p_graph,
           'hourly_graph': d_graph,
           'hourly_probes': h_graph }

def eventgraph(days=7,minthresh=500,medthresh=0,maxthresh=0,mac=False,output_format='eg'):
  q = {}
  
  if mac:
    q.update({'mac': mac })

  end = _now()
  start = end - _days(days)

  q.update({'day': {'$gt': start } })

  #debug('days: %s, min/med/max: %s/%s/%s' % ( days, minthresh, medthresh, maxthresh ))
  #debug(q)

  dailydb = list(db.probes.daily.find(q).sort([('day',1)]))

  probes = defaultdict(list)

  for e in dailydb:
    for h in e['probes']:
      tm = e['day'] + _hours(h)
      probes[e['mac']].append({'time': tm, 'probes': e['probes'][h]})

  csvoutput = ''
  egoutput = ''
  egoutputdate = ''

  jsonoutput = defaultdict()

  for mac in sorted(probes):
    t = 0
    hrs = []
    for tp in probes[mac]:
        t += tp['probes']
        hrs.append(tp['time'].astimezone(TZ).strftime('%Y/%m/%d %T'))
    
    if t < minthresh: # or t > maxthresh:
    #if (t > thresh) and (t < thresh_high):
      #print t, " too high or low ..."
      continue
    
    if output_format == 'eg':
      if not len(egoutput):
        egoutputdate = 'range = [%s, %s];' % ((int(start.strftime('%s')) * 1000), (int(end.strftime('%s')) * 1000))
        egoutput = 'data = ['

      egoutput += "  { name: '%s', data: [" % vendmac(mac,vendor_oui(mac))
    
      for h in sorted(hrs):
        egoutput += "new Date('%s')," % h
    
      egoutput += "] },  "
    elif output_format == 'json':
      if mac not in jsonoutput:
        jsonoutput[mac] = defaultdict(int)

      for h in sorted(hrs):
        if not jsonoutput[mac].has_key(h):
          jsonoutput[mac][h] = defaultdict(int)
        
        jsonoutput[mac][h] += probes[mac][h]
  
  if output_format == 'eg':
    egoutput += ']'
    return { 'range': egoutputdate, 'data': egoutput }
  else:
    return jsonoutput

def probes_per_hour():
  per = {}
  hourly_probes = db.probes.find({'_created': {'$gt': _now()-_hour(1)}}).count()
  per['second'] = '%.2f' % (hourly_probes / 60 / 60)
  per['minute'] = round(hourly_probes / 60,1)
  
  daily_probes = db.probes.find({'_created': {'$gt': _now()-_day(1)}}).count()
  per['hour'] = commify(round(daily_probes / 24,1))
  per['day'] = commify(daily_probes)
  
  return per

def heatmap():
  firstprobe = list(db.probes.find().sort([('_id',1)]).limit(1))[0]
  
  ftime = firstprobe['time']
  ftime -= _hours(ftime.hour)
  ftime -= _minutes(ftime.minute)
  
  probes = []
  
  lastprobe = list(db.probes.find().sort([('_id',-1)]).limit(1))[0]
  
  while ftime < dt.strptime(lastprobe['time'], '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=TZ):
      cnt = db.probes.find({'time':
                            {'$gt': ftime, '$lt': ftime + _days(1)}}).count()
      
      if cnt:
        probes.append({'date': ftime.isoformat(), 'count': cnt})

      ftime += _days(1)
  return probes

def rssiToMeters(rssi, m=1, ft=False):
  if rssi > -69:
    m = m - .05
  if rssi > -71:
    m = m - .05
  if rssi > -73:
    m = m - .05

  r = pow(10,((rssi*m) + 38.45) / TX_POWER)
  
  if ft:
    return '%.2f' % (r * 3.28084)
  else:
    return '%.2f' % r

######
##  Utilities
#####

#wtf does this du
def scrub_dict(d):
  if type(d) is dict:
      return dict((k, scrub_dict(v)) for k, v in d.iteritems() if v and scrub_dict(v))
  else:
      return d

# turn the list of hashes into name:entry hashes
def dictify(response,key):
  return {x[key]:x for x in response}

def deltafy(ts):
  return humanize.naturaldelta(ts)

def commify(num):
  if not num:
    return
  if num < 8000:
    return humanize.intcomma(num)
  
  return humanize.naturalsize(num,gnu=True,format='%.2f')

# idk
def rssi_loop():
  i = 0
  while True: 
    for mac in owndevs().keys():
      weight = weightedrssi(mac)
      if weight['weightedRssi'] == 0:
        continue
      #i = i + 1
      #if i > 5:
      #  i = 0

      #print "\n\t",weight['weightedRssi'], [ x for x in weight['meters'] ],"\n"
      for s in weight['seen_by']:
        print '%s: %s\t%s(%s)\t%sft\t%s\t(now: %s)\n' % (mac,s['_id'],
            s['lastrssi'],weight['weightedRssi'],
            rssiToMeters(s['lastrssi'],ft=True),
            s['lastseen'].astimezone(TZ).strftime('%F %T'),
            _now().strftime('%F %T'))
    time.sleep(5)

def locatable(mins=1, seenbymin=3, minrssi=-75, mac=False, owned_only=False, returnAll=False):
  avgrssi = 0
  locations = []
  locs = []
  poly = []
  probes = {}
  seenby = {}

  if minrssi > 0:
    minrssi = minrssi * -1

  location_pipeline = [
    {'$match':
      {
       '_created': {'$gt': _now() - _minutes(mins) },
       'rssi': {'$gt': minrssi },
      },
    },
    {'$group':
      {
       '_id': '$mac',
       'sensors': {'$addToSet': '$sensor'},
      },
    },
    {'$project':
      {
       '_id': '$_id',
       'sensors': '$sensors',
       'seenby': {'$size': '$sensors'},
       'mac': '$mac'
      },
     },
    { '$match': { 'seenby': { '$gte':  int(seenbymin)} } }
  ]

  res = list(db.probes.aggregate(location_pipeline))

  info('Got %d locatable probes' % len(res))

  sensors = dictify(db.sensors.find({},{'_id':False,'name':True,'longlat':True,'lastseen':True}),'name')
  
  for rec in res:
    mac = rec['_id']
    seenby[mac] = rec['sensors']
   
    for sensor in seenby[mac]:
      out = list(db.probes.find({'sensor': sensor, 'mac':mac,'_created': {'$gt': _now() - _minutes(mins) }}, {'_id': False}).limit(1))
      
      for probe in out:
        if 'longlat' not in sensors[probe['sensor']]:
          continue
        
        probe.update({'location':sensors[probe['sensor']]['longlat']})
        
        if probes.has_key(mac):
          probes[mac].append(probe)
        else:
          probes[mac] = [probe]

  for mac in probes:
    info(mac)
    avgrssi = 0
    locs = []
    
    for probe in probes[mac]:
      # for this to be accurate
      # need to send exactly 3 polygons
      # from 3 distinct points
      # duh.
      
      #loc = [probe['location']['coordinates'][1], probe['location']['coordinates'][0], probe['rssi']]
      avgrssi = avgrssi + probe['rssi']
      #poly = locToCircle(probe['location']['coordinates'][1],
      #                 probe['location']['coordinates'][0],
      #                 probe['rssi'])
      #loc = multilat(poly, probe['rssi'])
      #polys.append([[x[1],x[0]] for x in poly])
      locs.append([probe['location']['coordinates'][1], probe['location']['coordinates'][0], probe['rssi']])
      #locs.append([loc['centroid'].y, loc['centroid'].x, probe['rssi']])
      #rssis.append(probe['rssi'])
      #add loc, rssi, then multilat that?
   
    #avgrssi = avgrssi / len(probes[mac])
    location = multilat(locs)
    centroid = location['centroid']
    del location['centroid']

    locations.append({'mac': mac, 'time': _now(), 'data': location, # , 'rssi': avgrssi,
                      'seenby': seenby[mac], 'location': [centroid.y, centroid.x], })
                      #'locations': locs, 'data': location })
    
  return locations # { 'locations': locations, 'poly': poly, 'locs': locs }

def multilat(poly):
  availableLocations = len(poly)
  #info('Got %d locations' % availableLocations)
  multiplier = 1/1.2
  noOfTrueIntersections = 0
  circlesTooSmallForIntersection = 0
  intersection = 0
  derivedFrom = []

  while True:
    multiplier = multiplier * 1.05
    circlesTooSmallForIntersection = 0
    noOfTrueIntersections = 1
    derivedFrom = []

    intersection = sPoly(locToCircle(poly[0][0],poly[0][1], poly[0][2]))
    derivedFrom.append(poly[0])
    
    for i in range(1,availableLocations):
      info('Multilat: Bearing: %i' % i)

      newIntersection = intersection.intersects(sPoly(locToCircle(poly[i][0],poly[i][1],poly[i][2])))
      
      if ('newIntersection' in globals()):
        if (newIntersection.area < intersection.area):
          info('new Intersections: %d' % noOfTrueIntersections)
          noOfTrueIntersections = noOfTrueIntersections + 1
          intersection = newIntersection
          derivedFrom.append(poly[i])
      else:
        info('Small Circles: %d' % circlesTooSmallForIntersection)
        circlesTooSmallForIntersection = circlesTooSmallForIntersection + 1

    if (noOfTrueIntersections < 3) and (noOfTrueIntersections+circlesTooSmallForIntersection >= 3):
      info('Reached end: %s intersections' % noOfTrueIntersections)
      break

  return {
    'centroid': sPoly(intersection).centroid,
    'noOfCircles': noOfTrueIntersections,
    'area': round(sPoly(intersection).area * 100) / 100,
    'multiplier': multiplier,
    'derivedFrom': derivedFrom
  }   

  #return sPoly(intersection).centroid
  
def locToCircle(lng,lat,rssi):
  origin = [lng,lat]
  if origin[0] < origin[1]:
      x = origin[0]
      y = origin[1]
      origin = [y,x]

  distance = float(rssiToMeters(rssi))
  coords = []
  _coords = []

  #print origin
  for bearing in range(0,360):
    #print 'Bearing: %i' % bearing
    #print origin, bearing
    _coords.append(vincenty(kilometers=distance/1000).destination(origin,bearing))

  # turn LL into array rather than geopy points
  for c in _coords:
    coords.append([c.longitude,c.latitude])

  return coords

##
#   pcap handeling
##

# save uploaded pcap blob to capture directory, then readcaps()
def savecap(filename, data):
  with open('%s/%s' % (SIGMON_PCAP, filename), 'wb') as capfile:
    capfile.write(data)
  
  readcaps()

# read pcap upload directory and initiate pcap reader
def readcaps():
  for pcap_file in glob('%s/*.cap' % SIGMON_PCAP):
    try:
      readpcap(pcap_file)
    except Exception as e:
      debug('READ PCAPs: %s' % e)
      pass

# take a packet and add it to then probes collections
def readpcap(pcap_file):
  #bulk_probes = db.probes.initialize_unordered_bulk_op()

  sensor = re.sub(r'_.*',r'',os.path.basename(pcap_file))
  
  try:
    cap = pcapy.open_offline(pcap_file)
  except pcapy.PcapError, e:
    newfile = '%s/../errors/%s' % ( SIGMON_PCAP, os.path.basename(pcap_file) )
    error('Unable to read, moving %s to %s:' % (os.path.basename(pcap_file),os.path.dirname(newfile)))
    os.rename(pcap_file,newfile)
    return
 
  try:
    hdr = pkt = True
    
    while hdr and pkt:
      hdr,pkt = cap.next()
      
      if hdr and pkt:
        data = pcap_pktcb(sensor,hdr,pkt)
        if data:
          debug(pp(data))
          col.insert(data)
          os.unlink(pcap_file)
      else:
        print 'no header / packet!'
        pass
  except Exception as e:
    # called functions should raise exceptions
    debug('READ_PCAP: %s' % e)
    return
  
  # need to either mergecap into reasonably sized pcaps or
  # archive in some other way
  #if unsynced > 5:
  #  try:
  #    debug('Syncing PCAP probes')
  #    bulk_probes.execute()
  #  except BulkWriteError as bwe:
  #    debug('readcap(): bulk_probes: %s' % bwe.details)
  #  finally:
  #    unsynced = 0

  #unsynced = unsynced + 1


def pcap_pktcb(sensor, hdr, pkt):
  try:
    radio_packet = RTD.decode(pkt)
    dot11 = radio_packet.child()
    
    if dot11.get_type() == impacket.dot11.Dot11Types.DOT11_TYPE_MANAGEMENT:
      base = dot11.child().child()
      
      if base.__class__ != impacket.dot11.Dot11ManagementProbeRequest:
        return

      try:
        pktime = dt.fromtimestamp(hdr.getts()[0]).strftime('%F %T')
        signal = -(256-radio_packet.get_dBm_ant_signal())
      except:
        return

      bssid_base = dot11.child()

      try: ssid = unicode(base.get_ssid())
      except: ssid = ''

      seq = bssid_base.get_sequence_number()
      mac = getBssid(bssid_base.get_source_address())
      
      out = {
        'sensor': sensor,
        'mac':    mac,
        '_created':   dt.utcnow(),
        'time':   dt.utcnow(),
        'pktime': pktime,
        'ssid':   ssid,
        'rssi':   signal,
        'seq':    seq,
        'stats':  False,
       }

      return out

  except Exception as e:
    #debug('pcap_pktcb(): %s' % e)
    pass

def getBssid(arr):
  #Get Binary array to MAC addr format
  try:
    s = binascii.hexlify(arr)
    t = iter(s)
    st = ':'.join(a+b for a,b in zip(t,t))
  except Exception as e:
    debug('getBssid(): error - %s' % e)
    pass
  return st

def nl():
  logging.getLogger().setLevel('INFO')
  

# respond to various messages
def mqtt_message(client, userdata, msg):
  info('MQTT')
  info('MQTT: %s [%s]' % ( client, msg ))
  return

def mqtt_connected(client, userdata, flags, rc):
  info('Connected to MQTT Server %s' % SIGMON_MQTTT_URL)
  mqtt.subscribe('#')

def check_wireshark():
  wireshark_manuf = '%s/etc/manuf' % SIGMON_ROOT

  f = os.stat(wireshark_manuf)

  last_updated = time.time() - f[8]

  if (not f) or (last_updated > _week(1).total_seconds()):
    notice('oui-database','updating wireshark OUI database, last updated %s' % deltafy(last_updated))
    #macparser.update()

mongo = M(host=SIGMON_MONGO_URL, tz_aware=True, connect=True)
db   = mongo.sigmon
col  = db.probes
hostname = platform.node()

macparser = manuf.MacParser()

bulk_probes = bulk_daily = bulk_hourly = False
unsynced = 0

mqtt = mqttclient.Client()
mqtt.connect(SIGMON_MQTT_URL, SIGMON_MQTT_PORT, SIGMON_MQTT_KEEPALIVE)

mqtt.on_connect = mqtt_connected
mqtt.on_message = mqtt_message

check_wireshark()

info('Sigmon %s Loaded' % __name__)

if __name__ == '__main__':
  nl()
elif __name__ == 'app.sigmon':
  mqtt.publish('/sigmon/system','Sigmon %s Loaded' % __name__)
  pass

# vim: ts=2 sw=2 ai expandtab softtabstop=2
