#!/usr/bin/python -u
'''
probe.py v0.9i - cbt 10/01/14
'''

VERSION         = (0, 9,'i')
__version__     = '.'.join((str(_) for _ in VERSION))
__author__      = 'CB Terry <terry.chad@gmail.com>'
__url__         = 'https://github.com/terbo/sigmon'
__status__      = 'Prototype'
__description__ = 'Display/Record wireless probes like airodump-ng with wireshark '
__about__       = 'sigmon, or Signal Monitor, displays probe requests from wireless clients in range.'
__license__     = 'GPL v2'
__summary__     = 'sigmon has 3 modes: a full screen mode, which is the default; a debug mode, which prints out all info; and a tail mode, which will print probes in csv format.'

'''
last modified Jan 24 2016

taken from somewheres else ....
listen for wireless probe requests

TODO: WIN.

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

rewrite plans...


devices are becoming somewhat aware of advertising their preferred client list too often ..
perhaps make a fake open AP that gets all clients to try and register?
if it didn't complete the auth, but still got signal strength, would it deplete their
batteries if they stayed in the area too long? (for stores..)

'''

# read code, comment code, write code
# write code, write code, read code
# write code, comment code, comment code
# comment code, comment code, read code

import os, sys, tty, termios, signal, string
import re, time, getopt, threading, logging
import humanize as pp, datetime as dt
import ConfigParser

#logger = logging.getLogger('')
#logger.setLevel(logging.DEBUG)
#logformat = logging.Formatter('%(asctime)s %(threadName)s(%(lineno)d) -%(levelname)s: %(message)s')

#logfile = logging.FileHandler(re.sub(r'.py$','.log',__file__ ))
#logfile.setFormatter(logformat)

#consolelog = logging.StreamHandler(sys.stderr)
#consolelog.setFormatter(logformat)

#logger.addHandler(consolelog)
#logger.addHandler(logfile)

# cpickle is faster

try:
  import cPickle as pickle
except:
  import pickle

import bz2

import pyshark
import subprocess

from select import select
from threading import current_thread

from ansi.cursor import up, down, forward
from ansi.colour.fx import reset
from colors import bold as b, underline as ul, italic as i, negative as neg

import textwrap as text
from terminaltables import AsciiTable as Table

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
    return [ [ self.mac,
              avg(self.signal), max(self.signal), min(self.signal),
              self.signal[-1], list(self.bssids), self.probes, self.packets,
              self.dropped,
              dt.datetime.strftime(dt.datetime.fromtimestamp(
                float(self.firstseen)), '%X %D'),
              dt.datetime.strftime(dt.datetime.fromtimestamp(
                float(self.lastseen)), '%X %D'),
              self.interface ],
             [ list(self.ssids) if full == True else '' ] ,
             [ self.seen[x] for x in range(0,len(self.seen)) ] ,
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
    self.version = '0.9i'
    self.interfaces = set()
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
    
    # pickle options
    self.nopickles = False
    
    self.picklefile = '.sigmon.p'
    self.saveinterval = 300
    self.lastsaved = 0

    self.soundplayer = ''
    #self.soundplayeropts = ''
    self.soundnew = ''
    
    self.prompt = '>'
    
    self.getopts = 'Ppqhdtf:'
    self.getoptslong = ['help', 'quiet', 'debug', 'fav=', 'tail', 'print','nopickles']
    
    self.help_usage = ''' %s [options] [interface],...
          listen for wireless probe requests
           -h          show this help
      
           -p          mock curses output (default)
           -f          add a mac to favorite list (--fav [mac])
           -d          print debug to stdout, more for more info (--debug)
           -t          tailable (CSV) output (--tail)
           -P          disable saving .pickle file
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
''' 
      #o           set options?

# what bugs?
# log levels: [0] debug [1] verbose [2] everything

def debug(level, log):
  #logger.debug(log)
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
def getchar(prompt=True):
  fd = sys.stdin.fileno()
  old_settings = termios.tcgetattr(fd)
  ch=''
  try:
    tty.setraw(sys.stdin.fileno())
    if prompt: print conf.prompt, up(1)
    [i, o, e] = select([sys.stdin.fileno()], [], [], conf.screen_refresh)
    if i: ch=sys.stdin.read(1)
    else: ch=''
  finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
  return ch

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

# main packet processing function - called by XXX # scapy.sniff()
# somehow I can't get threads/timers to work in conjunction with scapy
# which presents its own problem - need to figure out what to do,
# or read from a db in a seperate program

def show_print(sig,sc):
  if 'trace' in conf.opts:
    return

  check_screensize()
  
  if 'tail' in conf.opts:
    return

  maxitems = int(conf.rows) - 19 # width of headers and spacing
  
  running_threads = ''
  for t in threading.enumerate():
    tname = t.getName()
    if tname != 'MainThread':
      running_threads += re.sub('sigmon-sniffer-',',',tname)
    #else:
    #  running_threads += '%s,' % tname

  running_threads = running_threads[1:]
  
  # changes the linux terminal title
  
  header = '\033]0;[%s] sigmon %s\007' % (conf.version, ', '.join(conf.interfaces))
  header += '\n  Started: %s ][ %s ]' % (pp.naturaltime(time.time()-conf.uptime), time.ctime())
  header += '[ %s Clients, %s SSIDs, %s Vendors ]' % \
      (pp.intcomma( len(conf.c) ), pp.intcomma( len(conf.ssids) ), len(conf.vendors))
  
  if conf.fulldisplay == True:
    header += '[ %s items sorted by %s' % ( maxitems, conf.defaultsort)
    header +=  ', filtering %s clients\n\n' % conf.viewfilter if conf.viewfilter else ''
    legend = ul('\n\tSTATION\t\t\t\t\t\tFirst Seen\t\tLast\t\tAvg/Min/Cur Sig\t#Probes\tSSIDs\n')
  else:
    header += '[ sorted by %s' % ( conf.defaultsort)
    legend = ul('\n\tSTATION\t\t\t\t\t\tSignal\t#Probes\tSSIDs\n')
  
  header += legend
  
  output = headers = {'all':'All','near':'Close','old':'Recently Seen','loud':'Loud','quiet':'Seldom Seen','far':'Farther'}
  
  try:
    for i, x in headers.items():
      output[i] = '%s %s %s\n' % (' ' * (int(conf.cols) / 2 - (len(str(x)+' Clients:') / 2) - 20), x, ' Clients:')
  except Exception as inst:
    debug(0,'ERROR output info: %s' % inst)

  # list clients, sorted by last seen
  
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
      if ssidscopy and len(', '.join(ssidscopy)) > 30:
        #debug(0, 'Length of ssids too long, re-formatting')

        ssids = '[%s] %s, %s ..' % ( len(ssidscopy), ssidscopy.pop(0), ssidscopy.pop(0) )

        if conf.filterdisplay == True:
        
          ssidtmp = ''
          for i in text.wrap(', '.join(ssidscopy), width=(int(conf.cols) - 24), \
              initial_indent='        ', subsequent_indent='        '):
            ssidtmp += '%s\n' % i
            maxitems -= 1
          
          ssids += '\n' + ssidtmp.rstrip()
      else:
        ssids = ', '.join(ssidscopy)
    except Exception as inst:
      debug(0,'ERROR Copying SSIDS: %s' % inst)

    if conf.fav.has_key(client):
      desc = '%s [%s]' % ( clients[client].vendor[:14], conf.fav[client][:8])
    
    desc = clients[client].vendor[:24]
    
    ## add to display
    if conf.fulldisplay == True:
              #mac  ven/desc  frst   last    savg smin sig   prob  ssids
      out += '%-18s (%-26s)   %18s   %18s    %-4s %-4s %-4s  %-6s  %s\n' % (client, desc, \
          dt.datetime.strftime(dt.datetime.fromtimestamp(float(clients[client].firstseen)), '%X %D'),  \
          pp.naturaltime(time.time()-float(clients[client].lastseen)),  \
          avg(clients[client].signal), min(clients[client].signal), ul(clients[client].signal[-1]), \
          pp.intcomma(clients[client].probes), ssids)
    else:
              #mac  ven/desc sig   prob  ssids
      out += '%-18s (%-26s)\t%-4s\t%-6s  %s\n' % (client, desc, \
          ul(clients[client].signal[-1]), pp.intcomma(clients[client].probes), \
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

  footer = '  sigmon %s on %s  -  %s probes' % \
      (conf.version, running_threads, pp.intcomma(conf.probes))

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
  print getchar(prompt=0)

def show_stats():
  threads = threading.activeCount()
  
  print 'conf.opts: %s ' % list(conf.opts)
   
  print 'Probes: %s' % pp.intcomma(conf.probes)
  print 'Packets: %s' % pp.intcomma(conf.packets)
  print 'Dropped: %s' % pp.intcomma(conf.dropped)
  print 'Signal Threshold: %s' % conf.signal_thresh
  print 'Clients seen: %s' % pp.intcomma(len(conf.c))
  print 'SSIDs seen: %s' % pp.intcomma(len(conf.ssids))
  print 'Vendors seen: %s' % len(conf.vendors)
  print 'Favorites list: %s' % list(conf.fav.items())
  print 'Interface list: %s' % list(conf.interfaces)
  print 'Start time: %s' % conf.uptime
  print 'Threads: %d' % threads
  
  print '\n\nPress q to exit, or choose an option:\n'
  print '[c]lients [a]ccess Points [S]ort [Q]uit [A]dd interface [D]ebug [T]hreads'
  #print '[ g ]  [ s ]  [ h ]  [ c ]  [ a ]  [ v ]  [ D ]  [ d ]  [ q ]'
  #print '                    Clients  APs  Vendors               quit'
  #print 'Graphs Statistics Help                    Debug  daemonize'
  print '\nsigmon %s' % conf.version
  
  waitkey()
  
def check_screensize():
  conf.rows, conf.cols = os.popen('stty size', 'r').read().split()

# key bindings -- a cleaner way ..
def check_input(sig,sc):
  if 'tail' in conf.opts:
    return
  
  inp = getchar()
  
  if not len(inp):
    return
  
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
  
  #elif inp == '':
  # from IPython import embed; embed() 
  
  elif inp == 'E':
    code = raw_input('Code to exec:')
    try:
      exec(code) in globals()
    except Exception as inst:
      pass
      #print 'Error in code: %s - %s' % ( code, inst)
    
    waitkey() 
  
  elif inp == 'q':
    sig_shutdown()
  
  elif inp == 's':
    print '[l] last seen [f] firstseen [p] probes',
    print '[P] probes desc [t] signal [T] signal desc',
    print '[v] vendor [V] vendor desc:  ',
    
    inp = getchar(prompt=0)
    
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
    print '%s vendors:' % len(conf.vendors)
    
    vendors = conf.vendors
    for vendor in sorted(vendors):
      print '%s: ' % vendor

      clients = conf.c
      for client in clients:
        if clients[client].vendor == vendor:
          print '\t%s - %s\t' % (client, time.ctime(float(clients[client].lastseen)))
    waitkey()

  elif inp == 'c':
    print '%s clients:' % len(conf.c)
    
    table = [['mac', 'sigavg/max/min/cur', 'bssids', 'probes/packets/dropped', 'first/lastseen', 'interface']]

    # make a copy, having errors with threads?
    clients = conf.c
    
    for mac in sorted(clients):
      (cl, ss, si, st) = clients[mac].pr()
      client = '%s (%s)' % ( clients[mac].vendor, cl[0] )
      signals = '%s/%s/%s - %s' % ( cl[1], cl[2], cl[3], cl[4] )
      ssids = ', '.join(clients[mac].ssids)
      packets = '%s/%s/%s' % ( cl[6] , cl[7] , cl[8] )
      firstseen = '%s/%s' % ( cl[9], cl[10] )
      iface = cl[11]
      
      table.append([client, signals, ssids, packets, firstseen, iface])
      
      #today = dt.datetime.today()
      #morning = time.mktime(dt.datetime.timetuple(dt.datetime(int(today.strftime('%Y')), \
      #    int(today.strftime('%m')),int(today.strftime('%d')))))
      
      #for hour in range(0,23):
      #  pass
      # .,;xX  traffic graph ...
    t = Table(table)
    print t.table
    waitkey()
  
  elif inp == 'a':
    print '%s ssids:' % len(conf.ssids)
    
    ssids = conf.ssids
    clients = conf.c
    
    for ssid in sorted(ssids):
      if ssid == '[ANY]':
        continue
      print '\t', ssid, ': ',
      c = 0
      for mac in clients:
        if ssid in clients[mac].ssids:
          c += 1
      print '%d searching client%c' % ( c, 's' if c > 1 else ' ')
    waitkey()
  
  elif inp == 'T':
    for thread in threading.enumerate():
      print '\t', thread
    waitkey()
  
  elif inp == 'A':
    print 'Enter monitor interface: ',
    inp = getchar(prompt=0)
    inp = int(inp)
    if inp not in range(0,99):
      print 'Enter a numeric interface. : ', inp
      waitkey()
      return

    iface = 'mon'+str(inp)

    try:
      start_sniffer([iface])
    except Exception as inst:
      debug(0,'ERROR Starting sniffer - %s' % inst)
      waitkey()
    finally:
      conf.interfaces.add(iface)
  
  elif inp == 'D':
    print '[0] off [1] verbose [2] debug [3] trace - Enter debug level: ',
    inp = getchar(prompt=0)

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
  
def loadconf(picklefile = False):
  global conf # why do I have to use this? seperate thread?
  try:
      conf = pickle.load(bz2.BZ2File(picklefile or conf.picklefile,'r'))
      conf.uptime = time.time()
      conf.running = 1
  except Exception as inst:
    print 'Error loading pickle session %s: %s' % ( conf.picklefile, inst)
    #finally:

def saveconf(picklefile = False):
  global conf
  try:
    pickle.dump(conf,bz2.BZ2File(picklefile or conf.picklefile,'w'))
    conf.lastsaved = time.time()
  except Exception as inst:
    print('Error saving state: %s' % inst)
  #finally:

def sig_shutdown():
  print '\nExiting ...',
  
  conf.running = 0
  
  signal.signal(signal.SIGALRM,signal.SIG_DFL)
  signal.signal(signal.SIGINT, signal.SIG_DFL)
  
  saveconf()
  
  # give threads time to exit
  
  time.sleep(1)
 
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
    
    elif opt in ('-p', '--print'):
      conf.opts.add('print')
    
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
  
    elif opt in ('-P','--nopickles'):
      conf.opts.add('nopickles')
    
  ifaces = re.findall('mon\d+',str(args))
  
  for iface in ifaces:
    iface = re.sub('\n','',iface)
    if iface not in conf.interfaces:
      conf.interfaces.add(iface)

def sniffprobes(iface):
  wireless_filter = '''
(wlan.fc.type_subtype == 4)
'''
#(wlan.fc.type == 2)
#(wlan.fc.type_subtype == 0 or wlan.fc.type_subtype == 1)

  #mac_re = re.compile('[0-9A-F][0-9A-F]:[0-9A-F][0-9A-F]:[0-9A-F][0-9A-F]',re.IGNORECASE)

  while conf.running:
    try:
      capture = pyshark.LiveCapture(interface=iface,display_filter=wireless_filter)
      debug(0,'Starting capture on interface %s' % iface)

      for packet in capture.sniff_continuously():
        try:
          signal = packet['radiotap'].dbm_antsignal
          bssid = packet['wlan'].da
          pktmac = packet['wlan'].ta
          ssid = packet['wlan_mgt'].ssid
        except:
          continue

        if ssid == 'SSID: ' or ssid == '' or ssid == ' ':
          ssid = '[ANY]'

        lastseen = time.time()

        thread = current_thread()

        match = re.search('mon(\d+$)', thread.name)
        curr_iface = match.group(0)

        conf.probes += 1

        # -- put this into a pickle
        #grep_shell = 'grep -i "%s" macs.txt' % mac_search

        # ugly way of reading custom mac file
        #try:
        #  vendor_result = subprocess.Popen(grep_shell,stdout=subprocess.PIPE,shell=True).communicate()[0]
        #  vendor_res = re.split(',',vendor_result) 
        #  vendor = vendor_res[0]
        #except:
        #  vendor = 'UNKNOWN'

        mac_vendor = pktmac[0:8]
        mac_search = re.sub('[\s:-]','',mac_vendor)
        mac_search = mac_search.upper()

        if mac_search in mac_manuf:
          vendor = mac_manuf.get(mac_search)
        else:
          vendor = 'UNKNOWN'
          
        if not conf.c.has_key(pktmac):
          debug(0,'New Client: %s ' % pktmac)

          conf.c[pktmac] = Client(pktmac)
          conf.c[pktmac].firstseen = lastseen
          conf.c[pktmac].vendor = vendor
          conf.c[pktmac].interface = curr_iface

          if vendor not in conf.vendors:
            conf.vendors.add(vendor)

        if bssid not in conf.c[pktmac].bssids:
          conf.c[pktmac].bssids.append(bssid)

        conf.c[pktmac].signal.append(signal)

        conf.c[pktmac].seen.append(lastseen)
        conf.c[pktmac].lastseen = lastseen
        
        firstseen = conf.c[pktmac].firstseen # just in case

        conf.c[pktmac].probes += 1

        if ssid not in conf.c[pktmac].ssids:
          debug(0,'New SSID for Client %s (%s) on interface %s @ %sdBm: %s'
                  % (pktmac, vendor, curr_iface, signal, ssid))

          if conf.soundplayer:
            subprocess.Popen(conf.soundplayer,conf.soundnew)

          conf.c[pktmac].ssids.append(ssid)

          if ssid not in conf.ssids:
            conf.ssids.add(ssid)

        if time.time() - conf.lastsaved > conf.saveinterval:
          saveconf()

        if 'tail' in conf.opts:
          show("'%s','%s','%s','%s','%s','%s','%s','%s'" %
            (pktmac, bssid, ssid, signal, firstseen, lastseen, curr_iface, vendor))
    
    except Exception as inst:
      debug(0,'Error in capture: %s - restarting' % inst)
    except AttributeError as inst:
      debug(0,'Error in capture: %s - restarting' % inst)

    # saveconf file periodically

def start_sniffer(ifaces):
  ## begin threads
  threads=[]
    
  for iface in ifaces:
    debug(1,'Creating thread sigmon-sniffer-%s' % iface)
    t = threading.Thread(target=sniffprobes,kwargs = \
        {'iface':iface}, name='sigmon-sniffer-%s' % iface)
    threads.append(t)
    
  for worker in threads:
    debug(0,'%s worker starting' % (worker.name))
    try:
      worker.daemon = True
      worker.start()
    except Exception as inst:
      debug(0,'FATAL %s worker error - %s' % (worker.name, inst))
      return False

def main(argv):
  global conf
  global mac_manuf
  
  # test for pickle file and load it otherwise initialize conf
  # which means you should move your pickle file if you want to start a new session
  # since the configuration precendence is
  #                runtime defaults => cfg file => pickle file => runtime flags
  # and -p <picklefile> or -P (no pickling) would overwrite any other attempts
  # at changing options - so -P will simply disable saving of a pickle file
  # (which will be defined when CONF() is instantiated
  
  conf = CONF()
  
  try:
    config = ConfigParser.ConfigParser()
    config.read(['sigmon.cfg', os.path.expanduser('~/.sigmonrc')])
   
    #conf.soundplayer = config.get('sound','player') or conf.soundplayer
    #conf.soundplayeropts = config.get('sound','playeropts')
    #conf.soundnew = config.get('sound','newsound') or conf.newsound
    conf.signal_thresh = abs(int(config.get('general','signal_thresh'))) - 100
    conf.screen_refresh = int(config.get('general','screen_refresh'))
    #conf.picklefile = config.get('general','picklefile')
  
    for iface, desc in config.items('interfaces'):
      if iface not in conf.interfaces:
        conf.interfaces.add(iface)

    for favmac,desc in config.items('favorites'):
      fav = re.sub(r'-',r':',favmac)
      conf.fav[fav] = desc
  
  except Exception as inst:
    debug(0,'ERROR reading sigmon.cfg or ~/.sigmonrc - %s' % inst)

  if os.path.isfile(conf.picklefile) and not conf.nopickles:
    print 'Loading session ...'
    loadconf()
  
  do_getopts(argv)
  
  if 'print' in conf.opts and 'tail' in conf.opts:
    conf.opts.remove('tail')
  
  if not 'tail' in conf.opts:
    conf.opts.add('print')
  
  # choose the default interface if none is specified
  if len(conf.interfaces) < 1:
    conf.interfaces.add('mon0')
      
  print 'Listening for probes from %s ' % \
    ( ', '.join(list(conf.interfaces)) )

  # on the specified interval, run show_print - print what is in conf.clients
  # sniff is running on another thread, so this updates automagically
  
  signal.signal(signal.SIGINT, sigint)
  signal.signal(signal.SIGALRM,show_print)
  signal.setitimer(signal.ITIMER_REAL,conf.screen_refresh)
  
  try:
    mac_manuf = pickle.load(bz2.BZ2File('mac_manuf.p','r'))
  except:
    print 'Error loading mac database ...'
    waitkey()

  start_sniffer(conf.interfaces)
  
  ## display csv header
  if 'tail' in conf.opts:
    print 'mac,bssid,ssid,signal,firstseen,lastseen,interface,vendor'

  while conf.running:
    try:
        show_print(1,2)
    except Exception as inst:
      # this displays very vague errors ...
      pass
      #print 'ERROR in main show_print: %s' % inst
      #waitkey()
    try:
        check_input(1,2)
    except Exception as inst:
      pass
      #print 'ERROR in main check_input: %s' % inst
      #waitkey()

  # bye lates
  sig_shutdown()

# fasten your helmets
if __name__ == '__main__':
    main(sys.argv[1:])

'''

scapy:
  <code>
    Started: a day ago ][ Mon Nov 17 00:21:00 2014 ][ 414 Clients, 405 SSIDs, 87 Vendors ][ 37 items sorted by last seen
    </code>

    pyshark:
    <code>
    Started: 37 minutes ago ][ Mon Nov 17 00:21:14 2014 ][ 335 Clients, 190 SSIDs, 45 Vendors ][ 37 items sorted by last seen
    </code>

    I thought that I was missing something.
    
    PyShark, the TShark (command line version of wireshark, network traffic analyzer) wrapper
    for python, seems to produce vastly greater results. The API is different, and though
    TShark does some mac address resolution, I havn't been able to access it.

    However, I've written some scripts to ensure the latest mac address database is available;
    fetching from the IEEE, wireshark, and nmap, and merging them. Wireshark has custom short
    descriptions, and nmap has a few extra OUI's. base64online.com comes up with many macs, will
    check out to make sure we have the most mac address vendors as possible. :)

    Going to run this and check it for several hours, then commit.
'''

# vim: ts=2 sw=2 et
