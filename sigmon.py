#!/usr/bin/python -u
'''
probe.py v.09f - cbt 10/01/14
last modified 17 oct 01:48 pst

taken from somewheres else ....
listen for wireless probe requests

TODO

Work out various displays, 'noisy' clients, common ssids

-- add redisplay/statistics/graphs
-- add multiple interfaces -> add ncurses

-- consolidate query scripts

BUGS

Malformed packets [may] squeak through, but less likely

calibration? 
cards report different power levels

dont use couchdb yet, takes massive space
'''

import os, sys, signal, string, re
import threading, datetime as dt, time
import logging, getopt, humanize as pp
from threading import current_thread
import ConfigParser, pprint, getch

logging.getLogger('scapy.runtime').setLevel(logging.ERROR) # quiet scapy ipv6 error

# the almighty scapies - packet crafting and manipulation
from scapy.all import sniff, Dot11, Dot11Elt
#load_module('p0f')

from netaddr import *     # MAC Address OUI Vendor Lookups - could offload to own db

# packet specification
# used to hold packet information before being placed into conf.client
class Packet:
  def __init__(self):
    self.lastseen=None
    self.firstseen=None
    self.mac=None
    self.ssid=None
    self.crypto=set()
    self.capability=None
    self.signal=0
    self.vendor=None
    self.gps=None
    self.channel=None
    self.packetype=None # bluetooth, wifi, nfc, cell
    self.ptype=0
    self.psubtype=0
    self.packets=0
    self.size=0
    self.location=None

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
  interface=None
  ostype=None
  dropped=None
  rate=None
  packets=0

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
class CONF:
  def __init__(self):
    self.version = '0.9c'
    self.interfaces = list()

    self.limit = 0
    self.packets = 0
    self.probes = 0
    self.uptime = 0
    
    # location for couchdb
    self.location = None
    
    # signal threshold for nearby devices
    self.signal_max = 0
    
    self.clientcount = 0
    self.ssidcount = 0
    
    self.fav = dict()
    self.c = dict() # clients
    self.opts = set() 
    
    self.db = None
    self.couch = None
    self.couchserver = ''
    
    self.sndplayer = ''
    self.sndplayeropts = ''
    self.newclientsound = ''
    
    self.getopts = 'qhi:df:l:tc'
    self.getoptslong = ['help', 'quiet','interface=', 'debug', 'couchdb=','fav=', 'limit=','tail', 'location=']

# what bugs?
# log levels: [0] debug [1] verbose [2] everything

def debug(level, log):
  if 'debug' not in conf.opts: return
  
  if level == 0 or \
      (level == 1 and 'verbose' in conf.opts) or \
      (level == 2 and 'trace' in conf.opts):
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
  if 'debug' not in conf.opts and \
      'tail' not in conf.opts:
    clear_screen()

  sys.stdout.write('%s\n' % out)
  sys.stdout.flush()

# main packet processing function - called by scapy.sniff()
# somehow I can't get threads/timers to work in conjunction with scapy
# which presents its own problem - need to figure out what to do,
# or read from a db in a seperate program

def sniffprobes(packet):
  p = Packet()
  thread = current_thread()
  
  match = re.search('mon(\d+$)', thread.name)
  curr_iface = match.group(0)
  
  # from fakeap callbacks
  if len(packet.notdecoded[8:9]) > 0:
    flags = ord(packet.notdecoded[8:9])
    if flags & 64 != 0:
      try:
        if not packet.addr2 is None:
          if packet.addr2 in conf.c:
            conf.c[packet.addr2].dropped += 1
          debug(2,'Dropping bad packet from %s on %s' % (packet.addr2, curr_iface))
          #return
      except:
        debug(2,'Dropping bad packet on %s' % curr_iface)
        #return
  
  # bad packets arent packets
  conf.packets += 1
  
  if conf.limit != 0 and conf.probes >= conf.limit:
    debug(0,'Saw %s probes, exiting.' % (conf.limit))
    sys.exit(0)
  
  #debug('Got ' + str(len(str(packet.payload))))
  # trying to determine packet size?
  
  # eliminate malformed/bad packets
  
  try: packet
  except:return debug(2,'No Packet')
  
  try: packet.info
  except: return debug(2,'No Packet')
  
  # check the mac later, maybe a mac class that returns xyz error
  try: p.mac = packet.addr2[:32]
  except: return debug(2,'No MAC Address')
  
  try: packet[Dot11].addr3
  except: return debug(2,'No BSSID Address')
  
  try: p.bssid = packet[Dot11].addr3[:18]
  except: return debug(2,'No BSSID Address(2)')

  p.lastseen = str(packet.time)
  p.size = packet.sprintf('%IP.len%')
  p.interface = curr_iface
  
  try:
    p.ptype = packet.type
    p.subtype = packet.subtype
  except:
    debug(2,'Cant get packet type')
    return
  
  p.signal = str(-(256-ord(packet.notdecoded[-4:-3])))
  
  try:
    mac = EUI(p.mac)
    oui = mac.oui
    p.vendor = oui.registration().org
  except TypeError:
    debug(0,'ERROR Resolving MAC: %s ' % (p.mac))
  except NotRegisteredError:
    p.vendor = 'UNREGISTERED'       # hackers change their macs ...
    return

  # if packet is a management/probe request
  if (packet.haslayer(Dot11) and packet.type == 0 and packet.subtype in (0,2,4)):
    p.ssid = str(packet[Dot11Elt].info.decode('utf-8')[:32]) if len(packet.info) else '<ANY>'
    p.ssid = re.sub('\n','',p.ssid)

    try: p.channel = ord(packet[Dot11Elt:3].info)
    except: p.channel = '0' # broadcast/any requests have no channel
    
    p.packetype = 'probe'
  
    # last filter for bad packets
    if p.ssid == None and p.bssid == None and p.mac == None: return

    try:
      conf.c[p.mac]
    except:
      debug(0,'New Client: ' + p.mac)
    
      conf.clientcount += 1
      
      conf.c[p.mac] = Client(p.mac)
      conf.c[p.mac].firstseen = p.lastseen
      conf.c[p.mac].vendor = p.vendor
      conf.c[p.mac].interface = p.interface
    
    conf.c[p.mac].bssid = p.bssid
    conf.c[p.mac].packets += 1
    conf.c[p.mac].signal.append(p.signal)
    conf.c[p.mac].lastseen = p.lastseen
    p.firstseen = conf.c[p.mac].firstseen
    
    # increment probe count
    conf.c[p.mac].probes += 1
    
    if p.ssid not in conf.c[p.mac].ssids:
      debug(0,'New SSID for Client %s (%s): %s' % (p.mac, p.vendor, p.ssid))
      # increment SSID count
      if p.ssid != '<ANY>': conf.ssidcount += 1
      conf.c[p.mac].ssids.add(p.ssid)
  
  else:
    # for layer in list(expand(packet)):
    # this won't work -- never will see a decrypted packet ..
    if p.mac in conf.c:
      if packet.haslayer(IP) and conf.c[p.mac].ostype == None:
        debug('Trying to discover %s OS ...' % p.mac)
        conf.c[p.mac].ostype = p0f(packet)
        try:
          debug(0,'Discovered %s is %s!' % p.mac, conf.c[p.mac].ostype)
        except:
          pass
      # some other type of packet
      else:
        conf.c[p.mac].packets += 1
    return

  # increment (relevant) packet count
  conf.probes += 1

  if 'tail' in conf.opts:
    show("'%s','%s','%s','%s','%s','%s','%s','%s'" % \
        (p.mac, p.bssid, p.ssid, p.signal, \
         p.firstseen, p.lastseen, p.interface, p.vendor))
  
  elif 'couchdb' in conf.opts:
    output = { 'mac': p.mac, 'bssid': p.bssid, 'ssid': p.ssid, 'signal': p.signal, \
                'firstseen': p.firstseen, 'lastseen': p.lastseen, 'vendor': p.vendor, \
                'location': conf.location, 'iface': p.interface }

    doc = ''
    
    try:
      doc = conf.db.save(output)
    except UnicodeDecodeError:
      debug(2,'Got some weird ssid - ' + p.ssid)
      
      #output['ssid'] = '' + p.ssid
      # still crashes on unicode / attack ssids ...
      #doc = conf.db.save(output)
    
    if doc != '':
      debug(1,'Created document %s' % doc['_id'])
      debug(2,'%s' % doc)
    
    if 'quiet' not in conf.opts:
        sys.stdout.write('%d\r' % conf.probes)

def expand(x):
  yield x.name
  while x.payload:
    x = x.payload
    yield x.name

def show_print():
  if 'tail' not in conf.opts:
    header = '\n %s probes [ Started: %s ][ %s ][ %s Clients ][ %s SSIDs ][ sorting by %s' % \
      ( pp.intcomma(conf.probes), \
        pp.naturaltime( time.time() - conf.uptime ), time.ctime(), \
        pp.intcomma( conf.clientcount ), pp.intcomma( conf.ssidcount ), 'last seen')
    
    legend = '\n  STATION\t\t\t\t\tPWR\tProbes\n\n'
    
    outputnear = '\n\n\t\t\t\t\tClose Clients:' + legend
    outputfar = '\t\t\t\t\tFarther clients:' + legend
    outputold = '\t\t\t\t\tOld Clients:' + legend

    # list clients, sorted by last seen
    # soon take key input and offer options . . 
    for client in sorted(conf.c, cmp=lambda a,b : cmp(conf.c[b].lastseen, conf.c[a].lastseen)):
      
      debug(0,'Outputting data for %s (%s) %sdBm [%s]' \
      % (client, conf.c[client].vendor, \
        conf.c[client].signal[-1], conf.c[client].probes))
    
      iface_res = re.search('(\d+)', conf.c[client].interface)
      iface = iface_res.group(0)
      
      # output list of clients and ssids
      
      if client in conf.fav.keys():
        out = iface + '  *'
      else:
        out = iface + '   '

      # easy way of only printing 'valid' ssids from the set
      
      ssids = ''.join(filter(lambda x:x in string.printable, \
                string.join(list(conf.c[client].ssids),',')))
      
      out += '%-18s (%-18s)\t%-8s %-8s %s\n' % (client, \
          conf.c[client].vendor[:18], conf.c[client].signal[-1], \
          conf.c[client].probes, ssids)
     
      # display clients that havn't been seen recently on the bottom
      if float(time.time()) - 60 > float(conf.c[client].lastseen):
        outputold += out
      # nearby signal
      elif int(conf.c[client].signal[-1]) > conf.signal_max :
        outputnear += out
      else:
      # far away signal
        outputfar += out

    show('%s \n %s \n %s \n %s' % (header, outputnear, outputfar, outputold)) 
def sigint(s, f):
  show_stats()
  time.sleep(1)

def show_stats():
  threads = threading.activeCount()
  
  print('conf.opts: ' + str(list(conf.opts)))
  print('Probes: ' + pp.intcomma(conf.probes))
  print('Packets: ' + pp.intcomma(conf.packets))
  print('Signal Maximum: ' + str(conf.signal_max))
  print('Clients seen: ' + pp.intcomma(conf.clientcount))
  print('SSIDs seen: ' + pp.intcomma(conf.ssidcount))
  print('Favorites list: ' + str(list(conf.fav.items())))
  print('Interface list: ' + str(list(conf.interfaces)))
  print('Start time: ' + str(conf.uptime))
  print('Threads: ' + str(threads))
  
  for thread in threading.enumerate():
    print '\t', thread

  prp = pprint.PrettyPrinter(indent=1, depth=6)
  for mac in conf.c:
    prp.pprint(conf.c[mac])
  
  print('\n\nPress q to exit, or choose an option:\n')
  print('[ g ]  [ s ]  [ h ]  [ c ]  [ a ]  [ v ]  [ D ]  [ d ]  [ q ]')
  print('                    Clients  APs  Vendors               quit')
  print('Graphs Statistics Help                    Debug  daemonize')
  print('\nsigmon %s' % conf.version)
  
  inp = getch.getch()

  if inp == 'q':
    sys.exit(1)
  elif inp == 's':
    show_stats()

def usage():
  print os.path.basename(__file__) + ' [options] [interface],...' + \
    '\tlisten for wireless probe requests\n'
  print '\t' + '-h' + '\t\t' + 'show this help'
  print ''
  print '\t' + '-f' + '\t\t' + 'add a mac to favorite list (--fav [mac])'
  print '\t' + '-c' + '\t\t' + 'use couchdb for output (--couchdb [server])'
  print '\t' + '  ' + '\t\t' + '  use --location [location] when using couchdb'
  print '\t' + '-l' + '\t\t' + 'stop after x number of packets (--limit [packets])'
  print '\t' + '-d' + '\t\t' + 'print debug to stdout, more for more info (--debug)'
  print '\t' + '-t' + '\t\t' + 'tailable (CSV) output (--tail)'
  print '\t' + '-q' + '\t\t' + 'quiet output (--quiet)'
  print ''
  print 'version ' + conf.version
  
  sys.exit(1)

def do_getopts(argv):
  try:
    opts, args = getopt.getopt(argv, conf.getopts, conf.getoptslong)
  except:
    print 'Argument error.'
    usage()

  for opt, arg in opts:
    if opt in ('-h', '--help'):
      usage()
    
    elif opt in ('-d', '--debug'):
      if 'verbose' in conf.opts:
        conf.opts.add('trace')
      
      elif 'debug' in conf.opts:
        conf.opts.add('verbose')
       
      conf.opts.add('debug')
    
    elif opt in ('-l', '--limit'):
      conf.limit = int(arg)
    
    elif opt in ('-q', '--quiet'):
      conf.opts.add('quiet')
    
    elif opt == '--location':
      conf.location = arg
    
    elif opt in ('-c', '--couchdb'):
      try:
        conf.couchdbserver = arg
      except: 
        pass

      try:
        import pycouchdb as couchdb
      except:
        print 'Please install pycouchdb (easy_install pycouchdb) before using CouchDB.'
        sys.exit(1)
      
      conf.opts.add('couchdb')
      
      debug(0,'Connecting to couchdb server %s' % conf.couchserver)
      
      try:
        conf.couch = couchdb.Server(conf.couchserver)
      except:
        debug(0,'Error initializing couchdb.' + conf.couch)
        sys.exit(2)

      try:
        conf.db = conf.couch.database('sigmon')
      except:
        conf.couch.create('sigmon')
        debug(0,'Creating database `sigmon`')
  
    elif opt in ('-f', '--fav'):
      # add a re for case -f mac=who --fav=mac=who?
      conf.fav[arg] = True
      debug(0,'added ' + arg + ' to favorites')
    
    elif opt in ('-t', '--tail'):
      conf.opts.add('tail')
    
  
  ifaces = re.findall('mon\d+',str(args))
  for iface in ifaces:
    iface = re.sub('\n','',iface)
    if iface not in conf.interfaces:
      conf.interfaces.append(iface)

def main(argv):
  global conf
  
  conf = CONF()
  conf.uptime = time.time()
  
  do_getopts(argv)

  config = ConfigParser.ConfigParser()
  config.read(['sigmon.cfg', os.path.expanduser('~/.sigmonrc')])
 
  conf.sndplayer = config.get('sound','player')
  conf.sndplayeropts = config.get('sound','playeropts')
  conf.newclientsound = config.get('sound','newclientsound')
  conf.couchserver = config.get('couch','server') 
  conf.signal_max = int(config.get('general','signal_max'))
  
  for favmac,desc in config.items('favorites'):
    fav = re.sub(r'-',r':',favmac)
    conf.fav[fav] = desc

  if 'quiet' not in conf.opts and 'debug' not in conf.opts \
      and 'tail' not in conf.opts and 'couchdb' not in conf.opts:
    conf.opts.add('print')
  
  # choose the default interface if none are specified
  if len(conf.interfaces) < 1:
    conf.interfaces.append('mon0')
      
  if 'couchdb' in conf.opts and conf.location == None:
    print 'Please provide a physical location name for couchdb.'
    sys.exit(2)

  conf.interfaces = sorted(conf.interfaces)
  
  #if len(conf.interfaces) > 1:
  #  conf.interfaces[-1] = 'and ' + conf.interfaces[-1]
  
  print 'Listening for %s probes from %s ' % \
    ( 'unlimited' if conf.limit == 0 else conf.limit, ', '.join(list(conf.interfaces)) )

  ## display csv header
  if 'tail' in conf.opts:
    print 'mac,bssid,ssid,signal,firstseen,lastseen,interface,vendor'
  
  ## begin threads
  threads=[]

  for interface in conf.interfaces:
    debug(1,'Creating thread sigmon-sniffer-'+interface)
    # sniff count packets, and do not store them in memory
    t = threading.Thread(target=sniff,kwargs={'prn':sniffprobes,'iface':interface,'store':0},
      name='sigmon-sniffer-' + interface)
    threads.append(t)
  
  signal.siginterrupt(3,True)
  
  for worker in threads:
    worker.daemon=True
    debug(0,'%s worker starting' % (worker.name))
    try:
      worker.start()
    except:
      debug(0,'FATAL %s worker error' % (worker.name))

  signal.signal(signal.SIGINT, sigint)
  
  try:
    while(7):
      time.sleep(3)
      show_print()
  
  except KeyboardInterrupt:
    threading.current_thread().join()
    
    show_stats()

if __name__ == '__main__':
    main(sys.argv[1:])

# vim: ts=2 sw=2 et
