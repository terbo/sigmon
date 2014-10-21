#!/usr/bin/python -u
'''
probe.py v.09d - cbt 10/01/14
last modified 17 oct 01:48 pst

taken from somewheres else ....
listen for wireless probe requests

TODO

Work out various displays, 'noisy' clients, common ssids

-- add redisplay/statistics/graphs
-- add threading -> add multiple interfaces -> add ncurses

-- consolidate query scripts
-- add threading!

BUGS

Malformed packets squeak through, and cause havok with string formatting

'''

import os, sys, signal, string, threading, datetime as dt, time # sched, json
import logging, getopt, humanize as pp
import npyscreen          # oooh preety

logging.getLogger('scapy.runtime').setLevel(logging.ERROR) # quiet scapy ipv6 error

from scapy.all import *   # the almighty scapies - packet crafting and manipulation
from netaddr import *     # MAC Address OUI Vendor Lookups - could offload to own db

# packet specification
# used to hold packet information before being placed into conf.client
class Packet():
  lastseen=None
  firstseen=None
  mac=None
  ssid=None
  crypto=set()
  capability=None
  signal=0
  vendor=None
  gps=None
  channel=None
  packetype=None # bluetooth, wifi, nfc, cell
  ptype=0
  psubtype=0
  packets=0
  size=0
  location=None

# client observation
class Client:
  mac=None
  firstseen=None
  lastseen=None
  probes=0
  ssids=set()
  bssid=None
  signal=list()
  channel=0
  vendor=None
  
  # so this is why it was only using one object/sharing values ...
  def __init__(self, mac):
    self.mac = mac
    self.ssids=set()
    self.firstseen=None
    self.lastseen=None
    self.probes=0
    self.bssid=None
    self.signal=list()
    self.vendor=None

# favorite mac addresses
class Fav:
  name=None
  mac=None

  def __init__(self, mac, name=''):
    self.mac = mac
    self.name = name

# the configuration object, with everything in it (including globals and defaults options)
class CONF(object):
  version = '0.9c'
  interfaces = set()

  limit = 0
  packets = 0
  probes = 0
  uptime = 0
  
  # location for couchdb
  location = None
  
  # signal threshold for nearby devices
  signal_max = -60
  
  clientcount = 0
  ssidcount = 0
  
  fav = set()
  
  sndplayer = '/usr/bin/play'
  sndplayeropts = '-V0'
  newsound = '/root/code/sigmon/new.wav'
  
  c = dict() # clients
  opts = set() 

  db = None
  couch = None
  couchserver = 'http://localhost:5984'
  
conf = CONF()

# what bugs?
def debug(log):
  if 'debug' not in conf.opts: return
  sys.stderr.write('%s  %s\n' % (dt.datetime.now(), log))
  sys.stderr.flush()
  
# TODO: remove all symbols, spaces, lowercase
def macreg(mac):
  return

# ansi clear screen - simulate airodump-ng
def clear_screen():
  sys.stdout.write('\033[2J')
  sys.stdout.write('\033[H')
  sys.stdout.flush()

# ansi print screen - simulate airodump-ng
def show(out):
  if 'debug' not in conf.opts and 'tail' not in conf.opts: clear_screen()
  sys.stdout.write('%s\n' % out)
  sys.stdout.flush()

def usage():
  print os.path.basename(__file__) + ' [interface] -i [interface...]' + \
    '\tlisten for wireless probe requests\n'
  print '\t' + '-h' + '\t\t' + 'show this help'
  print ''
  print '\t' + '-f' + '\t\t' + 'add a mac to favorite list (--fav [mac])'
  print '\t' + '-i' + '\t\t' + 'select interface (--interface [iface])'
  print '\t' + '-c' + '\t\t' + 'use couchdb for output (--couchdb [server])'
  print '\t' + '  ' + '\t\t' + '  use --location [location] when using couchdb'
  print '\t' + '-l' + '\t\t' + 'stop after x number of packets (--limit [packets])'
  print '\t' + '-d' + '\t\t' + 'print debug to stdout (--debug)'
  print '\t' + '-t' + '\t\t' + 'tailable (CSV) output (--tail)'
  print ''
  print 'version ' + conf.version
  
  sys.exit(1)

# main packet processing function - called by scapy.sniff()
# somehow I can't get threads/timers to work in conjunction with scapy
# which presents its own problem - need to figure out what to do,
# or read from a db in a seperate program

def sniffprobes(packet):
  
  p = Packet()
  
  conf.packets += 1
  
  if conf.limit != 0 and conf.probes >= conf.limit:
    debug('Saw %s probes, exiting.' % (conf.limit))
    sys.exit(0)
  
  #debug('Got ' + str(len(str(packet.payload))))
  # trying to determine packet size?
  
  # eliminate malformed/bad packets
  
  try: packet
  except:return #debug('No Packet')
  
  try: packet.info
  except: return #debug('No Packet')
  
  try: packet.addr2
  except: return #debug('No MAC Address')
  
  try: p.mac = packet.addr2 # check the mac later, maybe a mac class that returns xyz error
  except: return #debug('No MAC Address')
  
  try: packet[Dot11].addr3
  except: return #debug('No BSSID Address')
  
  try: p.bssid = packet[Dot11].addr3
  except: return #debug('No BSSID Address')

  p.lastseen = str(packet.time)
  p.size = packet.sprintf('%IP.len%')
  
  try:
    p.ptype = packet.type
    p.subtype = packet.subtype
  except:
    return
  
  p.signal = str(-(256-ord(packet.notdecoded[-4:-3])))
  
  try:
    EUI(p.mac)
    mac = EUI(p.mac)
    oui = mac.oui
    p.vendor = oui.registration().org
  except TypeError:
    debug('ERROR Resolving MAC: %s ' % (p.mac))
    next
  except NotRegisteredError:
    p.vendor = 'UNREGISTERED'       # hackers change their macs ...

  # if packet is a management/probe request
  if (packet.haslayer(Dot11) and packet.type == 0 and packet.subtype in (0,2,4)):
    p.ssid = packet[Dot11Elt].info[:32] if len(packet.info) else '<ANY>'
    try: p.channel = ord(packet[Dot11Elt:3].info)
    except: p.channel = '0' # broadcast/any requests have no channel
    
    p.packetype = 'probe'
  
    # last filter for bad packets
    if(p.ssid == None and p.bssid == None and p.mac == None): return

    try:
      conf.c[p.mac]
    except:
      debug('New Client: ' + p.mac)
      #subprocess.Popen([conf.sndplayer, conf.sndplayeropts, conf.newsound])
    
      conf.clientcount += 1
      
      conf.c[p.mac] = Client(p.mac)
      conf.c[p.mac].firstseen = p.lastseen
      conf.c[p.mac].vendor = p.vendor
    
    conf.c[p.mac].bssid = p.bssid
    conf.c[p.mac].signal.append(p.signal)
    conf.c[p.mac].lastseen = p.lastseen
    p.firstseen = conf.c[p.mac].firstseen
    
    # increment probe count
    conf.c[p.mac].probes += 1
    
    if(p.ssid not in conf.c[p.mac].ssids):
      debug('New SSID for Client %s (%s): %s' % (p.mac, p.vendor, p.ssid))
      # increment SSID count
      if p.ssid != '<ANY>': conf.ssidcount += 1
      conf.c[p.mac].ssids.add(p.ssid)
  
  else:
     # some other type of packet
     return

  # increment (relevant) packet count
  conf.probes += 1

  if 'print' in conf.opts:
    output = '\n %s probes [ Started: %s ][ %s ][ %s Clients ][ %s SSIDs ][ sorting by %s' % \
      ( pp.intcomma(conf.probes), \
        pp.naturaltime( time.time() - conf.uptime ), dt.datetime.today(), \
        pp.intcomma( conf.clientcount ), pp.intcomma( conf.ssidcount ), 'last seen')
    
    header = '\n STATION\t\t\t\t\tPWR\tProbes\n\n'
    
    outputnear = '\n\n\t\t\t\tClose Clients:' + header;
    outputfar = '\t\t\t\tFarther clients:' + header
    
    # list clients, sorted by last seen - soon take key input and offer options . . . . and sort by close and far
    for client in sorted(conf.c, cmp=lambda a,b : cmp(conf.c[b].lastseen, conf.c[a].lastseen)):
      
      if 'tail' not in conf.opts:
        debug('Outputting data for %s (%s) %sdBm [%s]' \
        % (client, conf.c[client].vendor, \
          conf.c[client].signal[-1], conf.c[client].probes))
      
      # output list of clients and ssids
      
      if(client in conf.fav): out = ' *'
      else: out = '  '

      # easy way of only printing 'valid' ssids from the set
      
      ssids = ''.join(filter(lambda x:x in string.printable, string.join(list(conf.c[client].ssids),',')))
      
      out += '%-18s (%-18s)\t%-8s %-8s %s\n' % (client, \
          conf.c[client].vendor[:18], conf.c[client].signal[-1], \
          conf.c[client].probes, ssids)
     
      # nearby signal
      if(int(conf.c[client].signal[-1]) > conf.signal_max) :
        outputnear += out
      else:
      # far away signal
        outputfar += out

      show(output + outputnear + '\n' + outputfar)
  
  elif 'tail' in conf.opts:
    show("'%s','%s','%s','%s','%s','%s','%s'" % \
        (p.mac, p.bssid, p.ssid, p.signal, \
         p.firstseen, p.lastseen, p.vendor))
  
  elif 'couchdb' in conf.opts:
    output = { 'mac': p.mac, 'bssid': p.bssid, 'ssid': p.ssid, 'signal': p.signal, \
                'firstseen': p.firstseen, 'lastseen': p.lastseen, 'vendor': p.vendor, \
                'location': conf.location}
    doc = conf.db.save(output)
    debug('Created document %s' % doc)
    
    sys.stdout.write('%d\r' % conf.probes)

def main(argv):
  conf.uptime = time.time()
  
  getopts = 'hi:df:l:tc'
  getoptslong = ['help', 'interface=', 'debug', 'couchdb=','fav=', 'limit=','tail', 'location=']
  
  try:
    opts, args = getopt.getopt(argv, getopts, getoptslong)
  except:
    print 'Argument error.'
    usage()

  for opt, arg in opts:
    if opt in ('-h', '--help'):
      usage()
    
    elif opt in ('-d', '--debug'):
      conf.opts.add('debug')
    
    elif opt in ('-l', '--limit'):
      conf.limit = int(arg)
    
    elif opt == '--location':
      conf.location = arg
    
    elif opt in ('-c', '--couchdb'):
      try:
        conf.couchdbserver = arg
      except: 
        pass

      if conf.location == None:
        print 'Please provide a physical location name for couchdb.'
        sys.exit(2)

      try:
        import pycouchdb as couchdb
      except:
        print 'Please install pycouchdb (easy_install pycouchdb) before using CouchDB.'
        sys.exit(1)
      
      conf.opts.add('couchdb')
      
      debug('Connecting to couchdb server %s' % conf.couchserver)
      
      try:
        conf.couch = couchdb.Server(conf.couchserver)
      except:
        debug('Error initializing couchdb.' + conf.couch)
        sys.exit(2)

      try:
        conf.db = conf.couch.database('sigmon')
      except:
        conf.couch.create('sigmon')
        debug('Creating database `sigmon`')
  
    elif opt in ('-f', '--fav'):
      conf.fav.add(arg)
      debug('added ' + arg + ' to favorites')
    
    elif opt in ('-t', '--tail'):
      conf.opts.add('tail')
    
    elif opt in ('-i', '--interface'):
      if arg not in conf.interfaces:
        conf.interfaces.add(arg)

  if('debug' not in conf.opts and 'tail' not in conf.opts and 'couchdb' not in conf.opts):
    conf.opts.add('print')
  
  if(len(conf.interfaces) < 1):
    conf.interfaces.add('mon0')
  
  print 'Listening for %s probes from %s ' % \
    ( 'unlimited' if conf.limit == 0 else conf.limit, list(conf.interfaces) )

  if('tail' in conf.opts):
    print 'mac,bssid,ssid,signal,firstseen,lastseen,vendor'
  
  threads=[]

  for interface in conf.interfaces:
    debug('Sniffer sigmon-sniffer-'+interface+' starting..')
    t = threading.Thread(target=sniff,kwargs={'prn':sniffprobes,'iface':interface,'store':0},
      name='sigmon-sniffer-' + interface)
    threads.append(t)
  
  signal.siginterrupt(3,True)
  
  for worker in threads:
    worker.daemon=True
    debug('%s worker starting' % (worker.name))
    try:
      worker.start()
    except:
      debug('FATAL %s worker error' % (worker.name))

  try:
    while(7):
      time.sleep(1)
      signal.pause()
  except KeyboardInterrupt:
    print('conf.opts: ' + str(list(conf.opts)))
    print('Probes: ' + pp.intcomma(conf.probes))
    print('Packets: ' + pp.intcomma(conf.packets))
    print('Signal Maximum: ' + str(conf.signal_max))
    print('Clients seen: ' + pp.intcomma(conf.clientcount))
    print('SSIDs seen: ' + pp.intcomma(conf.ssidcount))
    print('Favorites list: ' + str(list(conf.fav)))
    print('Interface list: ' + list(conf.interfaces))
    print('Start time: ' + str(conf.uptime))

    print('\n\nPress Ctrl-C again to exit, or choose an option:\n')
    print('[ g ]  [ s ]  [ h ]  [ c ]  [ a ]  [ v ]  [ D ]  [ d ]  [ q ]')
    print('                    Clients  APs  Vendors               quit')
    print('Graphs Statistics Help                    Debug  daemonize')
    print('\nsigmon %s' % conf.version)

  # sniff count packets, and do not store them in memory
  #sniff(iface=conf.interface, prn=sniffpkts, store=0)

if __name__ == '__main__':
    main(sys.argv[1:])

# vim: ts=2 sw=2 et
