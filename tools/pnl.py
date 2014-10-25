#!/usr/bin/python -u

# pnlscan.py v.05 - cbt  10/01/14

# taken from somewheres else ....
# listen for wireless probe requests and catalog them
#  look up the mac address, distribute the info
# made to run on n900 now ...

# IDEAS
#
#    Categorize mac addresses (common devices, uncommon)
#    Categorize essids - default, common, consumer
#    Flag changing mac's
#    Save data, maybe scan from multiple devices

# todo : gps and couchdb
#
# - found gps code, working from triggers
# - too many couchdb inserts - do this:
# - every minute (threading.Timer) insert 'weighted' ssids seen
# - if seen X times per minute, weight 100. X-1 w=80
# - modularize and class'ify?

import os, sys, time, sched, getopt #, json

import couchdb
from couchdb.mapping import Document, TextField, IntegerField, DecimalField

import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.all import *   # the almighty scapies
from netaddr import *     # MAC Address OUI Vendor Lookups

# from time import *
# from datetime import *

class Packet(Document):
  pktime = DecimalField()
  mac = TextField()
  bssid = TextField()
  ssid = TextField()
  crypto = TextField()
  capability = TextField()
  signal = IntegerField()
  vendor = TextField()
  gps = TextField()
  packetype = TextField()

def pnlsniff(pkt):
  crypto = set()
  ssid, channel, capability, macorg = '', '', '', ''
  
  try:
    pkt[Dot11Elt]
    bssid = pkt[Dot11].addr3
    pktime = str(pkt.time)
    pktmac = pkt.addr2
    sig_str = str(-(256-ord(pkt.notdecoded[-4:-3])))
  except: return

  "hackers change their macs"
  try:
    EUI(pktmac)
    mac = EUI(pktmac)
    oui = mac.oui
    macorg = oui.registration().org
  except NotRegisteredError:
    macorg = 'UNREGISTERED'
  except TypeError:
    next

  #if options('ess'):
  if (pkt.haslayer(Dot11) and pkt.type == 0 and pkt.subtype in (0, 2, 4)) and 'probe' in options:
    ssid = pkt[Dot11Elt].info if len(pkt.info) else '<EMPTY>'
    try: channel = ord(pkt[Dot11Elt:3].info)
    except: channel = '0'
    packettype = 'probe'
    
  #if options('probe'):
  elif (pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp)) and 'ess' in options:
    p = pkt[Dot11Elt]
    capability = pkt.sprintf("{Dot11Beacon:%Dot11Beacon.cap%}" "{Dot11ProbeResp:%Dot11ProbeResp.cap%}").split('+')
    packettype = 'broadcast'

    while isinstance(p,Dot11Elt):
      if p.ID == 0: ssid = p.info if len(p.info) else '<EMPTY>'
      elif p.ID == 3:
        try: channel = ord(p.info)
        except: channel = 0
      elif p.ID == 48: crypto.add('WPA2')
      elif p.ID == 221 and p.info.startswith('\x00P\xf2\x01\x01\x00'):
        crypto.add('WPA')
      p = p.payload
    if not crypto:
      if 'privacy' in capability: crypto.add('WEP')
      else: crypto.add('OPN')

  if ssid == None or bssid == None or pktmac == None: return

  if 'timer' in options:
    packet = Packet(
        {'time': pktime, 'mac': pktmac, 'bssid': bssid,
         'channel': channel, 'ssid': ssid, 'signal': sig_str,
         'crypto': str(' '.join(crypto)),
         'capability': str(' '.join(capability)),
         'vendor': macorg})
    
    seen.append(packet)
    try:
      macs[pktmac] = macs[pktmac] + 1
    except:
      macs[pktmac] = 1

    return

  if 'print' in options or 'couchdb' not in options:
    print '%s %s %s %s %s %s %s %s %s' % (pktmac, bssid, channel, ssid, sig_str+'dBm', pktime, ' '.join(crypto), capability, macorg)
  
  if 'couchdb' in options:
    try: couch
    except: couch = couchdb.Server()
    
    try:  db
    except: db = couch['packet']

    packet = Packet(
        {'time': pktime, 'mac': pktmac, 'bssid': bssid,
         'channel': channel, 'ssid': ssid, 'signal': sig_str,
         'crypto': str(' '.join(crypto)),
         'capability': str(' '.join(capability)),
         'vendor': macorg})
   # packet[pktime] = (pktmac, bssid, channel, ssid, sig_str, crypto, capability, macorg)
    #db.save(packet)
    #print json.dumps(packet)

options = set()
seen = list()
macs = dict()
limit = 0

def start_timer():
  s = sched.scheduler(time.time, time.sleep)
  
  s.enter(5, 1, printweight, (s,))
  s.run()
  
def printweight(p):
  print "Tryinjg!!"
  print macs
  start_timer()
  return

def main(argv):
  starttime = time.time()
  
  interface = ''
  
  options.add('probe')
  options.add('ess')
  
  getoptions = 'ci:thp'
  getoptionslong = ['help', 'print', 'probe', 'ess', 'interface=', 'couchdb']
  
  try:
    opts, args = getopt.getopt(argv, getoptions, getoptionslong)
  except:
    sys.exit(2)

  for opt, arg in opts:
    if opt in ('-h', '--help'):
      print os.path.basename(__file__) + ' [interface]'
      print '\t' + '-h' + '\t\t' + 'show this help'
      print ''
      print '\t' + '-i' + '\t\t' + 'select interface (--interface)'
      print '\t' + '-p' + '\t\t' + 'print to stdout (--print)'
      print '\t' + '-c' + '\t\t' + 'print json to stdout (--couchdb)'
      sys.exit()
    
    elif opt in ('-p', '--print'):
      options.add('print')
    
    elif opt in ('-t'):
      options.add('timer')
    
    elif opt in ('-c', '--couchdb'):
      options.add('couchdb')
    
    elif opt in ('-i', '--interface'):
      interface = arg
    
    elif opt in ('-l', '--limit'):
      options.add('limit')
      limit = arg
    
    elif opt in ('--probe'):
      options.remove('ess')
    
    elif opt in ('--ess'):
      options.remove('probe')

  if interface == '': interface = 'mon0' 
  print 'Listening for packets from ' + interface

  
  sniff(iface=interface, prn=pnlsniff)
#  start_timer()

if __name__ == "__main__":
    main(sys.argv[1:])

# filter arguments:
# --probe
# --ess
# --h
# --iface
# --search
# --searchmac
# --searchssid
# --searchcrypt
# --searchchan
# --searchvend
# --searchsig
# --print
# --couch
# --limit
# --verbose
# --runfor

#, lfilter=lambda p: (Dot11Beacon in p or Dot11ProbeResp in p))
# usage: airp
# vim: ts=2 sw=2 et
