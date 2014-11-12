#!/usr/bin/python -u
'''
probe.py v0.9h-2 - cbt 10/01/14
last modified 25 oct 12:58 pst

taken from somewheres else ....
listen for wireless probe requests

TODO

work on pcap import, and snoopy.db import

Work out various displays, 'noisy' clients, common ssids

-- add redisplay/statistics/graphs
-- add multiple interfaces -> add ncurses

-- consolidate query scripts

BUGS

Malformed packets [may] squeak through, but less likely
Malformed packets may mean clients not being seen
Tshark/Airodump-ng displays more clients

How do I display data from clients over time ...
To display patterns?


calibration? 
cards report different power levels

dont use couchdb yet, takes massive space

- change options during runtime
- data base like ...

'''

'''

rewrite plans:

after reading code for snoopy and airodump-iv I think I will
try and implement the methods that they used, classes, plugins,
curses, and clearer code organization.

Class Sniffer
Class Sigmon
Class Data?

save pcap, read pcap, save couch, save sql, save 
'''

# read code, comment code, write code
# write code, write code, read code
# write code, comment code, comment code
# comment code, comment code, read code

import os, sys, tty, termios, signal, string
import re, time, getopt, threading, logging
import humanize as pp, datetime as dt
import getch, ConfigParser

import pickle

from select import select
from threading import current_thread

from ansi.cursor import up, down
from ansi.colour.fx import reset
from colors import bold as b, underline as ul, italic as i, negative as neg

import textwrap as text

#import locale
#from gettext import gettext as _
#import i18n

#_ = i18n.language.ugettext #use ugettext instead of getttext to avoid unicode errors

logging.getLogger('scapy.runtime').setLevel(logging.ERROR) # quiet scapy ipv6 error

# the almighty scapies - packet crafting and manipulation
from scapy.all import sniff, Dot11, Dot11Elt, IP
#load_module('p0f')

from netaddr import *     # MAC Address OUI Vendor Lookups - could offload to own db

# packet observation
# used to hold packet information before being placed into conf.client
class Packet:
  def __init__(self):
    self.lastseen=None
    self.firstseen=None
    self.mac=None
    self.ssid=None
    self.bssid=None
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
  def __init__(self, mac):
    self.mac = mac
    self.ssids=list()
    self.firstseen=None
    self.lastseen=None
    self.probes=0
    self.bssids=list()
    self.signal=list()
    self.vendor=None
    self.rate=None
    self.dropped=0
    self.packets=0
    self.interface=None
    self.seen=list()
    self.sunc=0

  def pr(self,full=False):
    return [ [ self.mac, \
              avg(self.signal), max(self.signal), min(self.signal), self.signal[-1],\
              list(self.bssids), self.probes, self.packets, self.dropped, \
              dt.datetime.strftime(dt.datetime.fromtimestamp(float(self.firstseen)), '%X %D'), \
              dt.datetime.strftime(dt.datetime.fromtimestamp(float(self.lastseen)), '%X %D'), \
              self.interface ], \
             [ list(self.ssids) if full == True else '' ] , \
             [ self.seen[x] for x in range(0,len(self.seen)) ] , \
             [ self.signal[x] for x in range(0,len(self.signal)) ] ]

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
    self.version = '0.9h'
    self.interfaces = list()
    self.binary = os.path.basename(__file__)

    # screen refresh
    self.screen_refresh = 10

    self.running = 1

    self.packets = 0
    self.probes = 0
    self.dropped = 0
    self.uptime = time.time()
    
    # signal threshold for nearby devices
    self.signal_thresh = -62
    
    # filter clients not seen for 90 seconds
    self.seen_thresh = 90
    
    self.fulldisplay = True
    self.filterdisplay = True

    self.clientcount = 0
    self.ssidcount = 0
    self.vendorcount = 0
    self.vendors = set()

    self.fav = dict()
    self.c = dict() # clients
    self.ssids = set()
    self.opts = set() 
    self.search = None
    self.viewfilter = ''

    # used for screen calcs
    self.cols = 0
    self.rows = 0
    
    self.db = None
    
    self.defaultsort = 'last seen'
    
    # store packets or not?
    self.defaultstore = 0
    
    self.sndplayer = ''
    self.sndplayeropts = ''
    self.newclientsound = ''
    
    self.prompt = '\r> '
    
    self.getopts = 'qhdtf:'
    self.getoptslong = ['help', 'quiet', 'debug', 'fav=', 'tail']
    
    self.help_usage = ''' %s [options] [interface],...
          listen for wireless probe requests
           -h          show this help
      
           -f          add a mac to favorite list (--fav [mac])
           -d          print debug to stdout, more for more info (--debug)
           -t          tailable (CSV) output (--tail)
           -q          quiet output (--quiet)
      
      version %s''' % ( self.binary, self.version )
    
    self.help_keys = '''
      space       display status
      s           choose sort method
      a           show access point list
      c           show client list
      f           filter clients
      F           toggle filter view
      d           toggle verbose display
      \           search for mac or ssid
      /           highlight search
      T           show running threads
      A           add an interface
      D           set debug level
      o           set options?
''' 

# what bugs?
# log levels: [0] debug [1] verbose [2] everything

def debug(level, log):
  if 'debug' not in conf.opts: return
  
  if level == 0 or \
      (level == 1 and 'verbose' in conf.opts) or \
      (level == 2 and 'trace' in conf.opts):
    sys.stderr.write('\r%s  %s\n' % (dt.datetime.now(), log))
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
  if conf.search:
    out = re.sub(conf.search,neg(conf.search),out, flags=re.IGNORECASE)
  sys.stdout.write('%s\n' % out)
  sys.stdout.flush()

# non-blocking, non-portable getchar
def getchar():
  fd = sys.stdin.fileno()
  old_settings = termios.tcgetattr(fd)
  
  try:
    ch=''
    tty.setraw(sys.stdin.fileno())
    [i, o, e] = select([sys.stdin.fileno()], [], [], conf.screen_refresh)
    if i: ch=sys.stdin.read(1)
    else: ch=''
  except:
    pass
  finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    print '\r',ch,'\r',
    return ch
  
# main packet processing function - called by scapy.sniff()
# somehow I can't get threads/timers to work in conjunction with scapy
# which presents its own problem - need to figure out what to do,
# or read from a db in a seperate program

def sniffprobes(packet):
  if conf.running == 0:
    return

  p = Packet()
  thread = current_thread()
  
  match = re.search('mon(\d+$)', thread.name)
  curr_iface = match.group(0)
  
  # from fakeap callbacks
  if len(packet.notdecoded[8:9]) > 0:
    flags = ord(packet.notdecoded[8:9])
    if flags & 64 != 0:
      conf.dropped += 1

      try:
        if not packet.addr2 is None:
          if packet.addr2 in conf.c:
            conf.c[packet.addr2].dropped += 1
          debug(2,'Dropping bad packet from %s on %s' % (packet.addr2, curr_iface))
          #return
      except Exception as inst:
        debug(2,'Dropping bad packet on %s' % curr_iface)
        #return
  
  # bad packets arent packets
  conf.packets += 1
  
  # trying to determine packet size?
  # eliminate malformed/bad packets
  
  try: packet
  except: return # debug(2,'No Packet')
  
  try: packet.info
  except: return # debug(2,'No Packet')
  
  # check the mac later, maybe a mac class that returns xyz error
  try: p.mac = packet.addr2[:32]
  except: return # debug(2,'No MAC Address')
  
  try: packet[Dot11].addr3
  except: return # debug(2,'No BSSID Address')
  
  try: packet[Dot11].addr3[:18]
  except: return # debug(2,'No BSSID Address(2)')

  try:
    p.lastseen = str(packet.time)
    p.size = packet.sprintf('%IP.len%')
    p.interface = curr_iface
  except Exception as inst:
    debug(2,'ERROR getting packet time/size/iface - %s' % inst)
    return
  
  try:
    p.ptype = packet.type
    p.subtype = packet.subtype
  except Exception as inst:
    debug(2,'Cant get packet type - %s' % inst)
    return
  
  try:
    p.signal = str(-(256-ord(packet.notdecoded[-4:-3])))
  except:
    p.signal = 0
  
  try:
    mac = EUI(p.mac)
    oui = mac.oui
    p.vendor = oui.registration().org
  except TypeError:
    debug(1,'ERROR Resolving MAC: %s ' % (p.mac))
  except NotRegisteredError:
    debug(3,'ERROR Invalid MAC? : %s ' % (p.mac))
    return
    #p.vendor = 'UNREGISTERED'       # hackers change their macs ...

  # if packet is a management/probe request
  if (packet.haslayer(Dot11) and packet.type == 0 and packet.subtype in (0,2,4)):
    try:
      p.ssid = packet[Dot11Elt].info.decode('utf-8')[:32]
      p.ssid = re.sub('\n','',p.ssid)
    except:
      # bad packet?
      #p.ssid = '[UNKNOWN]'
      next
    if p.ssid == '':
      p.ssid = '[ANY]'

    try: p.channel = ord(packet[Dot11Elt:3].info)
    except: p.channel = '0' # broadcast/any requests have no channel
    
    p.packetype = 'probe'
  
    # last filter for bad packets
    if p.ssid == None and p.bssid == None and p.mac == None: return

    try:
      conf.c[p.mac]
    except:
      debug(0,'New Client: %s ' % p.mac)
    
      conf.clientcount += 1
      
      conf.c[p.mac] = Client(p.mac)
      conf.c[p.mac].firstseen = p.lastseen
      conf.c[p.mac].vendor = p.vendor
      conf.c[p.mac].interface = p.interface
    
    if p.bssid not in conf.c[p.mac].bssids:
      conf.c[p.mac].bssids.append(p.bssid)
  
    conf.c[p.mac].signal.append(p.signal)
    
    conf.c[p.mac].seen.append(p.lastseen)
    conf.c[p.mac].lastseen = p.lastseen
    p.firstseen = conf.c[p.mac].firstseen # just in case
    
    if p.vendor not in conf.vendors:
      conf.vendorcount += 1
      conf.vendors.add(p.vendor)
    
    # increment probe count
    conf.c[p.mac].probes += 1
    
    if p.ssid not in conf.c[p.mac].ssids:
      debug(0,'New SSID for Client %s (%s): %s' % (p.mac, p.vendor, p.ssid))
      
      # increment SSID count
      if p.ssid != '[ANY]': conf.ssidcount += 1
      conf.c[p.mac].ssids.append(p.ssid)
      if p.ssid not in conf.ssids:
        conf.ssids.add(p.ssid)
  
  else:
    if p.mac in conf.c:
      conf.c[p.mac].packets += 1
      
      '''
      if packet.haslayer(IP) and conf.c[p.mac].ostype == None:
        # this won't work -- never will see a decrypted packet ..
        # see the wifi stalking pdf
        debug('Trying to discover %s OS ...' % p.mac)
        conf.c[p.mac].ostype = p0f(packet)
        try:
          debug(0,'Discovered %s is %s!' % p.mac, conf.c[p.mac].ostype)
        except:
          pass
      # some other type of packet
      else:
      '''
    return

  # increment (relevant) packet count
  conf.probes += 1

  if 'tail' in conf.opts:
    show("'%s','%s','%s','%s','%s','%s','%s','%s'" % \
        (p.mac, p.bssid, p.ssid, p.signal, \
         p.firstseen, p.lastseen, p.interface, p.vendor))
  
def clientsort(a,b):
  sort = conf.defaultsort
  
  if(sort == 'last seen'):
    return cmp(conf.c[b].lastseen, conf.c[a].lastseen)
  elif(sort == 'first seen'):
    return cmp(conf.c[a].lastseen, conf.c[b].lastseen)
  elif(sort == 'probes'):
    return cmp(conf.c[b].probes, conf.c[a].probes)
  elif(sort == 'probes descending'):
    return cmp(conf.c[a].probes, conf.c[b].probes)
  elif(sort == 'power'):
    return cmp(conf.c[b].signal[-1], conf.c[a].signal[-1])
  elif(sort == 'power descending'):
    return cmp(conf.c[a].signal[-1], conf.c[b].signal[-1])
  elif(sort == 'vendor'):
    return cmp(conf.c[a].vendor, conf.c[b].vendor)
  elif(sort == 'vendor descending'):
    return cmp(conf.c[b].vendor, conf.c[a].vendor)

def show_print(sig,sc):
  if 'trace' in conf.opts:
    return

  check_screensize()
  
  if 'tail' not in conf.opts:
    maxitems = int(conf.rows) - 19 # width of headers and spacing
    
    running_threads = ''
    for t in threading.enumerate():
      tname = t.getName()
      if tname != 'MainThread':
        running_threads += re.sub('sigmon-sniffer-',',',tname)
    running_threads = running_threads[1:]
    
    header  = '\n  Started: %s ][ %s ]' % (pp.naturaltime(time.time()-conf.uptime), time.ctime())
    header += '[ %s Clients, %s SSIDs, %s Vendors ]' % \
        (pp.intcomma( conf.clientcount ), pp.intcomma( conf.ssidcount ), conf.vendorcount)
    if conf.fulldisplay == True:
      header += '[ %s items sorted by %s' % ( maxitems, conf.defaultsort)
      header +=  ', filtering %s clients\n\n' % conf.viewfilter if conf.viewfilter else ''
      legend = ul('\n\n\tSTATION\t\t\t\t\t\tFirst Seen\t\tLast\t\tAvg/Min/Cur Sig\t#Lost\t#Probes\tSSIDs\n')
    else:
      header += '[ sorted by %s' % ( conf.defaultsort)
      legend = ul('\n\n\tSTATION\t\t\t\t\t\tSignal\t#Lost\t#Probes\tSSIDs\n')
    
    header += legend
    
    try:
      output = headers = {'all':'All','near':'Close','old':'Recently Seen','loud':'Loud','quiet':'Seldom Seen','far':'Farther'}
      for i, x in headers.items():
        output[i] = '%s %s %s\n\n' % (' ' * (int(conf.cols) / 2 - (len(str(x)+' Clients:') / 2) - 20), x, ' Clients:')
    except Exception as inst:
      debug(0,'ERROR output info: %s' % inst)

    # list clients, sorted by last seen
    # soon take key input and offer options . . 
    
    clients = conf.c

    # for deciding wether or not to display client headers
    near = far = old = loud = quiet = all = 0

    for client in sorted(clients, cmp=lambda a, b: clientsort(a,b)):
      ssids = ''
      
      debug(0,'Outputting data for %s (%s) %sdBm [%s]' \
      % (client, clients[client].vendor, \
        clients[client].signal[-1], clients[client].probes))
    
      iface_res = re.search('(\d+)', clients[client].interface)
      iface = iface_res.group(0)
      
      # output list of clients and ssids
      
      # a way to key certain clients
      if client in conf.fav.keys():
        out = '%s  *' % iface
      else:
        out = '%s   ' % iface

      ## reformat SSIDS
      ssidscopy = sorted(clients[client].ssids)

      try:
        if ssidscopy and len(', '.join(ssidscopy)) > 32:
          #debug(0, 'Length of ssids too long, re-formatting')

          ssids = '[ %s ]\n' % b(len(ssidscopy))
          
          for i in text.wrap(', '.join(ssidscopy), width=(int(conf.cols) - 24), \
              initial_indent='        ', subsequent_indent='        '):
            ssids += '%s\n' % i
            maxitems -= 1
          ssids = ssids.rstrip()

        else:
          ssids = ', '.join(ssidscopy)
      except Exception as inst:
        debug(0,'ERROR Copying SSIDS: %s' % inst)

      try:
        conf.fav[client]
        desc = '%s [%s]' % ( clients[client].vendor[:14], conf.fav[client][:8])
      except:
        desc = clients[client].vendor[:24]
      
      ## add to display
      if conf.fulldisplay == True:
                #mac  ven/desc  frst   last    savg smin sig   drop  prob  ssids
        out += '%-18s (%-26s)   %18s   %18s    %-4s %-4s %-4s  %-6s  %-6s  %s\n' % (client, desc, \
            dt.datetime.strftime(dt.datetime.fromtimestamp(float(clients[client].firstseen)), '%X %D'),  \
            pp.naturaltime(time.time()-float(clients[client].lastseen)),  \
            avg(clients[client].signal), min(clients[client].signal), ul(clients[client].signal[-1]), \
            pp.intcomma(clients[client].dropped), pp.intcomma(clients[client].probes), ssids)
      else:
                #mac  ven/desc sig   drop prob  ssids
        out += '%-18s (%-26s)\t%-4s\t%-6s %-6s  %s\n' % (client, desc, \
            ul(clients[client].signal[-1]), pp.intcomma(clients[client].dropped), pp.intcomma(clients[client].probes), \
            ssids)
     
      if conf.filterdisplay:
        # loud client
        if len(clients[client].ssids) > 4 and maxitems>0 and (conf.viewfilter == '' or re.search('loud',conf.viewfilter)):
          loud += 1
          output['loud'] += out
          maxitems -= 1
        # hasnt been seen in x seconds
        elif float(time.time() - conf.seen_thresh) > float(clients[client].lastseen) and maxitems>0 and \
            (conf.viewfilter == '' or re.search('old',conf.viewfilter)):
          old += 1
          output['old'] += out
          maxitems -= 1
        # near by clients
        elif int(clients[client].signal[-1]) > conf.signal_thresh and maxitems>0 and \
            (conf.viewfilter == '' or re.search('near',conf.viewfilter)):
          near += 1
          output['near'] += out
          maxitems -= 1
        # far away clients
        elif int(clients[client].signal[-1]) < conf.signal_thresh and maxitems>0 and \
            (conf.viewfilter == '' or re.search('far',conf.viewfilter)):
          far += 1
          output['far'] += out
          maxitems -= 1
        # quiet clients, in the last 15 minutes
        elif clients[client].probes < 10 and maxitems>0 and (conf.viewfilter == '' or re.search('quiet',conf.viewfilter)):
          quiet += 1
          output['quiet'] += out
          maxitems -= 1
      else:
        if maxitems>0:
          output['all'] += out
          maxitems -= 1

    footer = '  sigmon %s on %s  -  %s/%s/%s probes/pkts/dropped' % \
        (conf.version, running_threads, pp.intcomma(conf.probes), \
         pp.intcomma(conf.packets), pp.intcomma(conf.dropped))
    footer += str(' ' * (int(conf.rows) - (int(conf.rows) - len(footer)) - 20)) + '[h]elp  [q]uit'
    clear_screen()
    
    show(down(int(conf.cols)-1))
    show(footer)
    show(up(conf.cols))
    show(header)
    
    if conf.filterdisplay:
      show(output['near'] if near else '')
      show(output['far'] if far else '')
      show(output['old'] if old else '')
      show(output['loud'] if loud else '')
      show(output['quiet'] if quiet else '')
    else:
      show(output['all'])

    show(down(int(conf.cols) - 6))
 
def avg(num):
  i = len(num)
  e = 0
  for a in num: e += int(a)
  return e / i

def sigint(s, f):
  if 'tail' in conf.opts:
    sig_shutdown()
  
  show_stats()
  check_input(1,2)

def waitkey():
  print '\nPress any key to continue: ',
  getch.getch()

def show_stats():
  threads = threading.activeCount()
  
  print 'conf.opts: %s ' % list(conf.opts)
   
  print 'Probes: %s' % pp.intcomma(conf.probes)
  print 'Packets: %s' % pp.intcomma(conf.packets)
  print 'Dropped: %s' % pp.intcomma(conf.dropped)
  print 'Signal Threshold: %s' % conf.signal_thresh
  print 'Clients seen: %s' % pp.intcomma(conf.clientcount)
  print 'SSIDs seen: %s' % pp.intcomma(conf.ssidcount)
  print 'Vendors seen: %s' % conf.vendorcount
  print 'Favorites list: %s' % list(conf.fav.items())
  print 'Interface list: %s' % list(conf.interfaces)
  print 'Start time: %s' % conf.uptime
  print 'Threads: %d' % threads
  
  print '\n\nPress q to exit, or choose an option:\n'
  print '[c]lients [a]ccess Points [S]ort [Q]uit [A]dd interface [D]ebug [T]hreads\n'
  #print '[ g ]  [ s ]  [ h ]  [ c ]  [ a ]  [ v ]  [ D ]  [ d ]  [ q ]'
  #print '                    Clients  APs  Vendors               quit'
  #print 'Graphs Statistics Help                    Debug  daemonize'
  print '\nsigmon %s' % conf.version
  
  waitkey()
  
def check_screensize():
  conf.rows, conf.cols = os.popen('stty size', 'r').read().split()

#Class Keys 
#['a':'access_points','x','xxx']
#for key, sub
#switch key: exec sub

# key bindings -- a cleaner way ..
def check_input(sig,sc):
  if 'tail' in conf.opts:
    return
  
  print conf.prompt,
  inp = getchar()
  
  if inp == 'h':
    print conf.help_keys
    waitkey()
  
  elif inp == ' ':
    show_stats()
  
  elif inp == '/':
    print 'Enter phrase to highlight: ',
    try:
      conf.search = raw_input()
    except:
      conf.search = ''
  
  elif inp == 'F':
    conf.filterdisplay = False if conf.filterdisplay == True else True
  
  elif inp == 'f':
    if conf.filterdisplay == False:
      print 'Filtering disabled, enable with "F"'
      waitkey()
      return
    vf = raw_input('Enter client filter [loud, quiet, far, near, old]:')
    if vf in ('loud','quiet','far','near','old'):
      conf.viewfilter = vf
    else:
      conf.viewfilter = ''

  elif inp == 'd':
    conf.fulldisplay = False if conf.fulldisplay == True else True
    
  elif inp == '\\':
    halfhr = 60 * 60 / 2
    sixhr = halfhr * 12
    halfdy = sixhr * 2
    day = halfdy

    print 'Enter MAC/SSID Address to search for:',
    search = raw_input()
    try:
      if re.search('[a-zA-Z0-0][-:][a-zA-Z0-9]',search):
        (cl, ss, st, si) = conf.c[search].pr(full=True)
        
        print cl
        print ss if ss else ''
        #print st if st else ''
        #print si if si else ''
        #seen_total = float(st[0]) - float(st[-1])
        #if(seen_total < halfhr):
      else:
        clients = conf.c
        print ''
        
        for client in sorted(clients, cmp=lambda a,b: cmp(clients[a].vendor, clients[b].vendor)):
          ssids = clients[client].ssids
          if search in ssids:
            (cl, ss, si, st) = clients[client].pr(full=True)
            print clients[client].vendor
            print '\t',
            print cl
            print '\t',
            print ss

      waitkey()
    except Exception as inst:
      print '%s not found - %s' % (search, inst)
      waitkey()
  
  elif inp == 'E':
    code = raw_input('Code to exec:')
    try:
      exec(code) in globals()
    except Exception as inst:
      print 'Error in code: %s - %s' % ( code, inst)
    
    waitkey() 
  
  elif inp == 'q':
    sig_shutdown()
  
  elif inp == 's':
    print '[l] last seen [f] firstseen [p] probes',
    print '[P] probes desc [t] signal [T] signal desc',
    print '[v] vendor [V] vendor desc:  ',
    
    inp = getchar()
    
    if inp == 'l':
      conf.defaultsort = 'last seen'
    elif inp == 'f':
      conf.defaultsort = 'first seen'
    elif inp == 'p':
      conf.defaultsort = 'probes'
    elif inp == 'P':
      conf.defaultsort = 'probes descending'
    elif inp == 't':
      conf.defaultsort = 'power'
    elif inp == 'T':
      conf.defaultsort = 'power descending'
    elif inp == 'v':
      conf.defaultsort = 'vendor'
    elif inp == 'V':
      conf.defaultsort = 'vendor descending'
    else:
      print 'Invalid entry'
      return

    print 'Changing sort method to %s' % conf.defaultsort
    time.sleep(0.6)
  
  elif inp == 'v':
    print '%s vendors:' % conf.vendorcount
    
    vendors = conf.vendors
    for vendor in sorted(vendors):
      print '%s: ' % vendor

      clients = conf.c
      for client in clients:
        if clients[client].vendor == vendor:
          print '\t%s - %s\t' % (client, time.ctime(float(clients[client].lastseen)))
    
    waitkey()

  elif inp == 'c':
    print '%s clients:' % conf.clientcount
    
    print '\tmac, sigavg, sigmax, sigmin, signal, bssid, probes,',
    print 'packets, dropped, first, lastseen, interface\n'

    # make a copy, having errors with threads?
    clients = conf.c
    
    for mac in sorted(clients):
      (cl, ss, si, st) = clients[mac].pr()
      print clients[mac].vendor
      print cl
      print ss
      print '\t', list(clients[mac].ssids)
      
      #today = dt.datetime.today()
      #morning = time.mktime(dt.datetime.timetuple(dt.datetime(int(today.strftime('%Y')), \
      #    int(today.strftime('%m')),int(today.strftime('%d')))))
      
      #for hour in range(0,23):
      #  pass
      # .,;xX  traffic graph ...
    waitkey()
  
  elif inp == 'a':
    print '%s ssids:' % conf.ssidcount
    
    ssids = conf.ssids
    clients = conf.c
    
    for ssid in sorted(ssids):
      print '\t', ssid, ': ',
      for mac in clients:
        clients = 0
        if ssid in ssids:
          clients += 1
        print '%d clients' % clients
    waitkey()
  
  elif inp == 'T':
    for thread in threading.enumerate():
      print '\t', thread
    waitkey()
  
  elif inp == 'A':
    print 'Enter monitor interface to run on: ',
    inp = getchar()
    try:
      start_sniffer(['mon'+str(inp)])
    except Exception as inst:
      debug(0,'ERROR Starting sniffer - %s' % inst)
      waitkey()
  
  elif inp == 'D':
    print '[0] off [1] verbose [2] debug [3] trace - Enter debug level: ',
    inp = getchar()

    if inp == 0:
      try:
        conf.opts.remove('trace')
        conf.opts.remove('verbose')
        conf.opts.remove('debug')
      except Exception as inst:
        pass
    elif inp == 1:
      conf.opts.add('debug')
    elif inp == 2:
      conf.opts.add('debug')
      conf.opts.add('verbose')
    elif inp == 3:
      conf.opts.add('debug')
      conf.opts.add('verbose')
      conf.opts.add('trace')
    else:
      print 'Invalid selection: ', inp
      waitkey()
    return
  
def sig_shutdown():
  print '\nExiting ...',
  
  conf.running = 0
  
  signal.signal(signal.SIGALRM,signal.SIG_DFL)
  signal.signal(signal.SIGINT, signal.SIG_DFL)
  
  # give threads time to exit
  time.sleep(1)
  try:
    pickle.dump(conf,open('sigmon.p','wb'))
  except Exception as inst:
    print('Error saving state: %s' % inst)

  sys.exit(0)

def do_getopts(argv):
  try:
    opts, args = getopt.getopt(argv, conf.getopts, conf.getoptslong)
  except Exception as inst:
    print 'Argument error - %s' % inst
    print conf.help_usage
    sys.exit(1)

  for opt, arg in opts:
    if opt in ('-h', '--help'):
      print conf.help_usage
      sys.exit(0)
    
    elif opt in ('-d', '--debug'):
      if 'verbose' in conf.opts:
        conf.opts.add('trace')
      
      elif 'debug' in conf.opts:
        conf.opts.add('verbose')
       
      conf.opts.add('debug')
    
    elif opt in ('-q', '--quiet'):
      conf.opts.add('quiet')
    
    elif opt in ('-f', '--fav'):
      # add a re for case -f mac=who --fav=mac=who?
      conf.fav[arg] = True
      debug(0,'added %s to favorites' % arg)
    
    elif opt in ('-t', '--tail'):
      conf.opts.add('tail')
  
  ifaces = re.findall('mon\d+',str(args))
  for iface in ifaces:
    iface = re.sub('\n','',iface)
    if iface not in conf.interfaces:
      conf.interfaces.append(iface)

def start_sniffer(ifaces):
  ## begin threads
  threads=[]
  
  for interface in ifaces:
    debug(1,'Creating thread sigmon-sniffer-%s' % interface)
  
    # sniff count packets, and do not store them in memory
    t = threading.Thread(target=sniff,kwargs= \
        {'prn':sniffprobes,'iface':interface, 'store':conf.defaultstore},
          name='sigmon-sniffer-%s' % interface)
    
    threads.append(t)
    
  for worker in threads:
    debug(0,'%s worker starting' % (worker.name))
    try:
      worker.daemon = True
      worker.start()
    except Exception as inst:
      debug(0,'FATAL %s worker error - %s' % (worker.name, inst))

def main(argv):
  global conf
  
  # test for sigmon.p and load it otherwise initialize conf
  sessionfile = '.sigmon.p'
  
  if os.path.isfile(sessionfile):
    print 'Loading session ...'
    try:
      conf = pickle.load(open(sessionfile,'rb'))
      conf.uptime = time.time()
    except Exception as inst:
      print 'Error loading sessionfile %s: %s' % ( sessionfile, inst)
      sys.exit(1)

  else:
    conf = CONF()

  try:
    config = ConfigParser.ConfigParser()
    config.read(['sigmon.cfg', os.path.expanduser('~/.sigmonrc')])
   
    conf.sndplayer = config.get('sound','player')
    conf.sndplayeropts = config.get('sound','playeropts')
    conf.newclientsound = config.get('sound','newclientsound')
    conf.signal_thresh = abs(int(config.get('general','signal_thresh'))) - 100
    conf.screen_refresh = int(config.get('general','screen_refresh'))
  
    for iface, desc in config.items('interfaces'):
      if iface not in conf.interfaces:
        conf.interfaces.append(iface)

    for favmac,desc in config.items('favorites'):
      fav = re.sub(r'-',r':',favmac)
      conf.fav[fav] = desc
  
  except Exception as inst:
    debug(0,'ERROR reading sigmon.cfg or ~/.sigmonrc - %s' % inst)

  do_getopts(argv)
  
  if 'quiet' not in conf.opts and 'debug' not in conf.opts \
      and 'tail' not in conf.opts:
    conf.opts.add('print')
  
  # choose the default interface if none is specified
  if len(conf.interfaces) < 1:
    conf.interfaces.append('mon0')
      
  conf.interfaces = sorted(conf.interfaces)
  
  print 'Listening for probes from %s ' % \
    ( ', '.join(list(conf.interfaces)) )

  ## display csv header
  if 'tail' in conf.opts:
    print 'mac,bssid,ssid,signal,firstseen,lastseen,interface,vendor'
  
  # on the specified interval, run show_print - print what is in conf.clients
  # sniff is running on another thread, so this updates automagically
  
  signal.signal(signal.SIGINT, sigint)
  signal.signal(signal.SIGALRM,show_print)
  signal.setitimer(signal.ITIMER_REAL,conf.screen_refresh)
  
  start_sniffer(conf.interfaces)
  
  # change the linux terminal title

  print "\033]0;sigmon %s [%s]\007" % (conf.version, ', '.join(conf.interfaces))

  while conf.running:
    try:
        show_print(1,2)
    except Exception as inst:
      print 'ERROR in main show_print: %s' % inst
      waitkey()
    try:
        check_input(1,2)
    except Exception as inst:
      print 'ERROR in main check_input: %s' % inst
      waitkey()


  # bye lates
  sig_shutdown()

# fasten your helmets
if __name__ == '__main__':
    main(sys.argv[1:])

# vim: ts=2 sw=2 et
