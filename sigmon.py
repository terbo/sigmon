#!/usr/bin/python -u

# probe.py v.09a - cbt 10/01/14

'''
taken from somewheres else ....
listen for wireless probe requests

TODO
Need a pretty print for uptime (number_format)
and for the date

'''

import os, sys, time, getopt # sched, json
import logging
logging.getLogger('scapy.runtime').setLevel(logging.ERROR)

from scapy.all import *   # the almighty scapies - packet crafting and manipulation
from netaddr import *     # MAC Address OUI Vendor Lookups - could offload to own db
from commands import *
from subprocess import *

# packet specification: used to hold packet information before being placed into conf.client
class Packet():
  lastseen=None
  mac=None
  ssid=None
  crypto=set()
  capability=None
  signal=0
  vendor=None
  gps=None
  channel=None
  packetype=None # bluetooth, wifi, nfc, cell
  packets=0

# client observation
class Client:
  mac=None
  firstseen=None
  lastseen=None
  probes=0
  ssids=set()
  bssid=None
  signal=0
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
    self.signal=0
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
  version = '0.9a'
  c = dict() # clients
  opts = set() 
  limit = 0
  packets = 0
  uptime = 0
  signal_max = -60
  clientcount = 0
  ssidcount = 0
  fav = set()

conf = CONF()

# debug?
def debug(log):
  if 'debug' not in conf.opts: return
  '''
  try:
    debugoutput
  except:
    debugoutput = ''

  debugoutput += log + '\n'
  '''
  print log
  
# remove all symbols, spaces, lowercase
def macreg(mac):
  return

# ansi clear screen - simulate airodump-ng
def clear_screen():
  sys.stdout.write('\033[2J')
  sys.stdout.write('\033[H')
  sys.stdout.flush()

# ansi print screen - simulate airodump-ng
def show(out):
  clear_screen()
  print out
  print '\n'
#  print debugoutput


# main packet processing function - called by scapy.sniff()
# somehow I can't get threads/timers to work in conjunction with scapy
# which presents its own problem - need to figure out what to do,
# or read from a db in a seperate program

def sniffpkts(packet):
  #if('limit' in conf.opts and conf.packets >= conf.limit): sys.exit(0)
  
  p = Packet()
  
  # eliminate malformed/bad packets
  try: packet
  except:return debug('No Packet')
  try: packet[Dot11].addr3
  except: debug('No BSSID Address')
  try: packet.addr2
  except: debug('No MAC Address')
  
  #debug(packet.sprintf("Packet size: %IP.len%"))
  #debug(packet[0].show())
  
  try:
    p.bssid = packet[Dot11].addr3
    p.lastseen = str(packet.time)
    p.mac = packet.addr2
    p.signal = str(-(256-ord(packet.notdecoded[-4:-3])))
  except: 
    debug('Cant get SSID/Address/Signal ..')
    return
 
  if(p.bssid == None or p.mac == None or p.signal == 0):
   return

  
  try:
    EUI(p.mac)
    mac = EUI(p.mac)
    oui = mac.oui
    p.vendor = oui.registration().org
  except NotRegisteredError:
    p.vendor = 'UNREGISTERED'       # hackers change their macs ...
  except TypeError:
    debug('ERROR Resolving MAC: ' + str(p.mac))
    return

  # if packet is a management/probe request
  if (packet.haslayer(Dot11) and packet.type == 0 and packet.subtype in (0, 2, 4)) and 'probe' in conf.opts:
    p.ssid = packet[Dot11Elt].info if len(packet.info) else '<ANY>'
    try: p.channel = ord(packet[Dot11Elt:3].info)
    except: p.channel = '0' # broadcast/any requests have no channel
    p.packetype = 'probe'
  
    # last filter for bad packets
    if(p.ssid == None and p.bssid == None and p.mac == None): return

    try:
      conf.c[p.mac]
      conf.c[p.mac].lastseen = p.lastseen
    except:
      debug('New Client: ' + p.mac)
      subprocess.Popen(['/usr/bin/play','-q','/root/build/kismet-2013-03-R1b/wav/new.wav'])
    
      conf.clientcount += 1
      
      conf.c[p.mac] = Client(p.mac)
      conf.c[p.mac].firstseen = p.lastseen
      conf.c[p.mac].vendor = p.vendor
    

    conf.c[p.mac].bssid = p.bssid
    conf.c[p.mac].signal = p.signal # TODO: make a list to show signal overtime
    
    # increment probe count
    conf.c[p.mac].probes += 1
    
    if(p.ssid not in conf.c[p.mac].ssids):
      debug('New SSID for Client ' + p.mac + '(' + p.vendor + '): ' + p.ssid)
      # increment SSID count
      if p.ssid != '<ANY>': conf.ssidcount += 1
      conf.c[p.mac].ssids.add(p.ssid)
  
  
  # increment packet count
  conf.packets += 1

  # re-add couchdb support later
  if 'print' in conf.opts:

    output = '\n PKTS: ' + str(conf.packets) + ' [ Elapsed: ' + str(int((time.time() - conf.uptime))) + \
        ' ][ ' + str(int(time.time())) + ' ][ ' + str(conf.clientcount) + ' Clients ][ ' + str(conf.ssidcount) + ' SSIDs ][ sorting by signal level\n'
    
    header = '\n STATION\t\t\t\tPWR\tFrames\tProbes\n\n'
    
    outputnear = '\n\t\t\t\tClose Clients:\n' + header;
    outputfar = '\t\t\t\tFarther clients:\n' + header
    
    # list clients, sorted by signal - soon take key input and offer options . . . . and sort by close and far
    for client in sorted(conf.c, cmp=lambda a,b : cmp(conf.c[b].lastseen, conf.c[a].lastseen)):
      
      debug('Outputting data for ' + str(client) + ' (' + str(conf.c[client].vendor) + ') ' + conf.c[client].signal + \
          ' [' + str(conf.c[client].probes))
      # output list of clients and ssids
      
      out = ''
      
      #if(client in conf.fav): out = '*'
      
      out += ' ' + str(client) + ' (' + str(conf.c[client].vendor[:9]) + ')\t\t' + \
        str(conf.c[client].signal) + '\t' + \
        str(conf.c[client].probes) + '\t' + ','.join(conf.c[client].ssids) + '\n'
      
      # nearby signal
      if(int(conf.c[client].signal) > conf.signal_max) :
        outputnear += out
      # far away signal
      else:
        outputfar += out

    outputnear += '\n\n\n\n'
    
    if 'debug' not in conf.opts: show(output + outputnear + outputfar)

def main(argv):
  conf.uptime = time.time()
  interface = ''
  
  conf.opts.add('probe')
  conf.opts.add('print')

  getopts = 'ci:thpdf'
  getoptslong = ['help', 'print', 'probe', 'interface=', 'debug', 'fav=']
  
  try:
    opts, args = getopt.getopt(argv, getopts, getoptslong)
  except:
    print 'err'
    sys.exit(2)

  for opt, arg in opts:
    if opt in ('-h', '--help'):
      print os.path.basename(__file__) + ' [interface]'
      print '\t' + '-h' + '\t\t' + 'show this help'
      print ''
      print '\t' + '-i' + '\t\t' + 'select interface (--interface)'
      print '\t' + '-p' + '\t\t' + 'print to stdout (--print)'
      print '\t' + '-c' + '\t\t' + 'print json to stdout (--couchdb)'
      print '\t' + '-d' + '\t\t' + 'print debug to stdout (--debug)'
      sys.exit()
    
    elif opt in ('-p', '--print'):
      conf.opts.add('print')
    
    elif opt in ('-d', '--debug'):
      conf.opts.add('debug')
    
    elif opt in ('-i', '--interface'):
      interface = arg
    
    elif opt in ('-l', '--limit'):
      conf.opts.add('limit')
      limit = arg
    
    elif opt in ('--probe'):
      conf.opts.remove('ess')
    
    elif opt in ('--ess'):
      conf.opts.remove('probe')

  if interface == '': interface = 'mon0' 
  print 'Listening for packets from ' + interface

  sniff(iface=interface, prn=sniffpkts)

if __name__ == '__main__':
    main(sys.argv[1:])

# vim: ts=2 sw=2 et
