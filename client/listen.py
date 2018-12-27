#!/usr/bin/env python2
VERSION = '0.9-dev2.51 0.051b'

# TODO: upload zipped csv & pcap files
# Threading. Listen on multiple interfaces. - x the problems?

""" catch all exceptions """

import sys, os, time, resource
import datetime, logging, urllib3
from platform import node
from logging import debug, info, error
import pcapy, impacket, json, binascii
from impacket import ImpactDecoder
from impacket.dot11 import frequency as dot11_frequencies
from logging.handlers import RotatingFileHandler
import signal
from py_daemon import py_daemon

class Sensor(py_daemon.Daemon):
  def __init__(self):
    self.starttime = time.time()
    self.version = VERSION

    self.debug   = os.environ.get('SIGMON_DEBUG', 1)
    self.detach   = os.environ.get('SIGMON_DETACH', 1)
    self.apihost  = os.environ.get('SIGMON_API_HOST', '1.0.0.1')
    self.apiport  = os.environ.get('SIGMON_API_PORT', 8989)
    self.apiprobes  = os.environ.get('SIGMON_API_PROBES', '/probes/')
    self.apiaps  = os.environ.get('SIGMON_API_APS', '/aps/')
    self.apidata  = os.environ.get('SIGMON_API_APS', '/datapkts/')
    self.homedir = os.environ.get('SIGMON_ROOT', '/data/sigmon')
    
    self.apiurls = {'datapkts': '%s' % ( self.apidata ),
                    'probes': '%s' % ( self.apiprobes ),
                    'aps': '%s' % ( self.apiaps )}
    
    self.logcsv = os.environ.get('SIGMON_CSVOUT', 0)
    self.logjson = os.environ.get('SIGMON_JSONOUT', 0)
    self.logweb = os.environ.get('SIGMON_WEBOUT',1)
    self.logpcap = os.environ.get('SIGMON_SAVEPCAP',0)
    self.watchaps = os.environ.get('SIGMON_WATCHAPS',1)
    self.watchdata = os.environ.get('SIGMON_WATCHDATA',0)
    self.watchprobes = os.environ.get('SIGMON_WATCHPROBES',1)
    
    self.savelogs = os.environ.get('SIGMON_SAVELOGS',1)
    
    self.poststatus = os.environ.get('SIGMON_POSTSTATUS',1)
    
    self.statusurl = os.environ.get('SIGMON_STATSURL', '/logs.sensors/')
    
    self.usefilter = os.environ.get('PCAP_FILTER',0)

    self.iface = os.environ.get('SIGMON_MON_DEV', 'mon0')
    self.queue_time = os.environ.get('QUEUE_TIME', 25)
    self.queue_packets = os.environ.get('QUEUE_PACKETS', 50)
    
    
    self.apsleep = 10
    self.datasleep = 3

    self.pcapfile = {}
    
    self.max_errors = 25
    self.statusprint = 60 * 7

    self.scriptname = os.path.basename(__file__).replace('.py','')
    self.hostname = node() 
    self.pidfile = '%s.pid' % ( self.scriptname ) 
    
    self.errorlog = []
    
    self.csvdelim = ','
    self.csvquote = '"'
     
    self.aps = {}
    self.macs = {}

    self.synced = 0
    self.last_synced = 0
    self.last_status = ''
    self.last_synced_status = 0
    self.errors = 0

    self.logfile = 'logs/%s.%s.%s-%s.log' % ( 
                                           self.scriptname,
                                           self.hostname,
                                           self.iface,
                                           datetime.datetime.now().strftime('%F'))
    
    self.log_format = '%(asctime)s %(module)s:%(lineno)d : %(levelname)s : %(message)s'
    self.logger = logging.getLogger()
    
    if self.savelogs:
      self.logger.setLevel(logging.DEBUG)
      self.log_handler = RotatingFileHandler(self.logfile, maxBytes=5000000, backupCount=20)
      self.log_handler.setFormatter(logging.Formatter(self.log_format))
      self.logger.addHandler(self.log_handler)
    
    if self.debug:
      self.log_stderr = logging.StreamHandler(sys.stderr)
      self.log_stderr.setFormatter(logging.Formatter(self.log_format))
      self.log_stderr.setLevel(logging.DEBUG)
      self.logger.addHandler(self.log_stderr)

    # pcapy settings
    self.pcap_filter = 'type mgt subtype probe-req' # need to add probe resp
    self._max_pkts = -1
    self._max_len = 1514
    self._promisc = 1
    self._read_timeout = 100
   
    self.pcap_maxsize = 500000

    self.data = {
        'datapkts': [],
        'probes': [],
        'aps': [],
    } 
    
    self.pcapdump = {}

    self.maxpoolsize = 4
    self.maxpooltimeout = None

    self.http_headers = urllib3.util.make_headers(keep_alive=True,
                                          user_agent='sigmon sensor %s' % self.version)
    self.http_headers.update({'Content-Type':'application/json'})

    self.pool = urllib3.HTTPConnectionPool(self.apihost, self.apiport,
                                      self.maxpoolsize,
                                      self.maxpooltimeout,
                                      headers=self.http_headers)
    self.RTD = ImpactDecoder.RadioTapDecoder()
    
    self.active = False
    
    # called like such before instantiation
    if self.detach:
      py_daemon.Daemon.__init__(self,self.pidfile,verbose=True)
    
  
  def error(self,err):
      error(err)
      self.errors += 1
      self.errorlog.append('%s %s' % (datetime.datetime.now().strftime('%F-%T'), err))

  def do_exit(self):
    if self.queued():
      error('Exiting, wrote %s packets to csv in %s' % (self.writecsv(), self.homedir))
    # called like such after instantiation
    super(Sensor,self).stop()

  def status(self):
    self.last_synced_status = time.time()

    memusage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss 
    
    self.last_status = {
      'sensor': self.hostname,
      'uptime': self.uptime().total_seconds(),
      'memusage': memusage,
      'pktseen': self.pkts,
      'synced': self.synced,
      'lastsync': self.last_synced,
      'queued': { x: len(self.data[x]) for x in self.data.keys() },
      'time':   time.time(),
      'version': self.version,
      'active': self.active,
      'errorcount': self.errors,
      'errors': self.errorlog,
    }
    
    if self.logpcap:
      for pcapf in self.pcapdump:
        stat = os.stat(self.pcapfile[pcapf])
        
        if stat and stat[6] > self.pcap_maxsize:
          self.pcapture()
    
    if self.debug:
      info('uptime: %s' % self.last_status['uptime'])
      info('memory usage: %.2fmb' % (self.last_status['memusage']))
      info('synced: %d packets (%d errors)' % \
        ( self.synced, len(self.errorlog) ))
      info('queued: %s, last synced: %.2f seconds ago' % \
        (self.last_status['queued'], (time.time() - self.last_status['lastsync'])))
    
    if self.poststatus:
      self.post(self.statusurl, data=self.last_status)
    
    return self

  def writejson(self):
    written = 0

    for field in self.data.keys():
      for pkt in self.data[field]:
        print(self.csvify(pkt))

  def writecsv(self):
    written = 0

    with open('%s/csv/%s_%s-%s.csv' % (self.homedir, self.hostname, self.iface,
      datetime.datetime.now().strftime('%F-%T')), 'a') as csvfile:
      for field in self.data.keys():
        for pkt in self.data[field]:
          written += 1
          csvfile.write('%s\n' % self.csvify(pkt))

    return written
  
  def queued(self):
    return sum([ len(self.data[field[0]]) for field in zip(self.data)])
  
  def queue(self, data):
    ptype = data['ptype']
    self.data[ptype].append(data)
    
    if self.queued() > self.queue_packets or \
        time.time() - self.last_synced > self.queue_time:
        self.sync()
    
    return self
  
  def uptime(self):
    return datetime.timedelta(seconds=(time.time() - self.starttime))

  def sync(self):
    if self.savelogs:
      self.log_handler.flush() 
    
    try:
      # i dont save pcap here, thats immediately written
      # could make it another queued data hash...
      for field in self.data.keys():
        if len(self.data[field]):
          if self.logjson:  self.writejson()
          if self.logcsv:   self.writecsv()
          if self.logweb:   self.post(self.apiurls[field],field=field)

    except Exception as e:
      self.error('upload: %s (on %s)' % (e, field))
    
    
    if time.time() - self.last_synced_status > self.statusprint:
      self.status()

    return self
  
  def post(self, url, data=False, field=False):
    r = ''
    
    try:
      if field:
        encoded_data = json.dumps(self.data[field])
      elif data:
        encoded_data = json.dumps(data)
      else:
        error('Sent no data? url:%s data:%s field:%s' % ( url, data, field ))
        return

      response = self.pool.urlopen('POST', url, body=encoded_data,
                                         headers=self.http_headers,
                                         assert_same_host=False)
      r = response.read()
      
      if field:
        self.synced += self.queued()
        self.last_synced = time.time()
        self.data[field] = []
  
    except Exception as e:
      self.error('Posting to %s: %s/%s (posting %s/%s)' % ( url, e, r, field, data))

  def csvify(self,data):
    return self.csvdelim.join( [ '%s%s%s' % \
          (self.csvquote,data[x],self.csvquote) for x in data.keys()])

class Listener(Sensor):
  def __init__(self):
    Sensor.__init__(self)
  
  def run(self):
    debug('iface: %s ip: %s port %s endpoint %s/%s' % \
        (self.iface, self.apihost, self.apiport, self.apiprobes,self.apiaps))
    debug('sync: ap:%s data:%s probes:%s  to web:%s csv:%s json:%s pcap:%s' % \
        (self.watchaps, self.watchdata, self.watchprobes, self.logweb, self.logcsv, self.logjson, self.logpcap))
    
    info('syncing every %s seconds/%s packets)' % \
        (self.queue_time, self.queue_packets))

    self.pkts = 0
    
    self.active = True
    self.listen()
  
  def listen(self):
    info('listening... on %s ..' % self.iface)
    
    while self.active:
      try:
        self.cap = pcapy.open_live(self.iface, self._max_len,
                              self._promisc, self._read_timeout)
        if self.usefilter:
          self.cap.setfilter(self.pcap_filter)
        
        if self.logpcap:
          self.pcapture()
        
        debug('%s: net=%s, mask=%s, linktype=%s' % \
           (self.iface, self.cap.getnet(), self.cap.getmask(), self.cap.datalink()))
        
        self.cap.loop(-1, self.pktcb)
      
      except Exception as e:
        if self.errors > self.max_errors:
          self.error('I cant work in an environment like this. Bye.')
          self.do_exit()
        
      finally:
        if self.active:
          self.error('error(%d) while sniffing: %s' % ( self.errors, e ))
          info('sleeping for %d seconds' % (self.errors * 4))
          time.sleep(self.errors * 4)
  
  def pcapture(self):
    for field in self.data.keys():
      self.pcapfile[field] = '%s/pcap/%s.%s.%s-%s.pcap' % \
       ( self.homedir, self.hostname, self.iface, field, \
           datetime.datetime.now().strftime('%F-%T'))
      info('Opening PCAP file for %s: %s' % ( field, self.pcapfile[field]))
      self.pcapdump[field] = self.cap.dump_open(self.pcapfile[field])
        
  def getbssid(self,arr):
    #Get Binary array to MAC addr format
    s = binascii.hexlify(arr)
    t = iter(s)
    st = ':'.join(a+b for a,b in zip(t,t))
    return st

  def get_channel(self, frequency):
    return dot11_frequencies[frequency[0]]

  def pktcb(self, hdr, pkt):
    self.pkts += 1
    
    try:
      radio_packet = self.RTD.decode(pkt)
      dot11 = radio_packet.child()
      base = dot11.child().child()
      bssid_base = dot11.child()
    except:
      return
    
    if dot11.get_type() == impacket.dot11.Dot11Types.DOT11_TYPE_MANAGEMENT:
      try:
        src_mac = self.getbssid(bssid_base.get_source_address())
        dst_mac = self.getbssid(bssid_base.get_destination_address())
      except: # encrypted/malformed/uninteresting
        return

      if base.__class__ == impacket.dot11.Dot11ManagementProbeRequest:
        ptype = 'probes'
      elif base.__class__ == impacket.dot11.Dot11ManagementBeacon:
        if self.watchaps:
          ptype = 'aps' 
          if src_mac in self.aps and (time.time() - self.aps[src_mac]) < self.apsleep:
            return # seen recently
          else:
            self.aps[src_mac] = time.time()
        else: # not watching aps
          return
      else:
        if self.watchdata:
          ptype = 'datapkts'
          try:
            data = dot11.child()
            dst_mac = self.getbssid(data.get_source_address()) # its switched... !
            src_mac = self.getbssid(data.get_destination_address())
            #if src_mac in self.macs and (time.time() - self.macs[src_mac]) < self.datasleep:
            #  return # seen recently
            #else: 
            self.macs[src_mac] = time.time()
          except: # malformed/encrypted
            return
        else: # not watching datapkts
          return
    else: # not management packet
      return
      
    if not self.watchprobes:
      return
    
    try: signal = -(256-radio_packet.get_dBm_ant_signal())
    except: return # error('pktcb: signal: %s' % e)

    try: channel = self.get_channel(radio_packet.get_channel())
    except: channel = 1 # This only reports what channel the interface is on..

    bssid_base = dot11.child()

    try: ssid = unicode(base.get_ssid())
    except: ssid = ''
      
    try:
      seq = bssid_base.get_sequence_number()
    
      seentime = datetime.datetime.now().isoformat()
      (a,b) = hdr.getts()
      pktime = '%d.%d' % (a,b) # don't discard microseconds
          
    except Exception as e:
      self.error('pktcb Exception(%d)! %s' % ( self.errors, e))
      return

    if self.logpcap:
      try:
        self.pcapdump[ptype].dump(hdr, pkt)
      except Exception as e:
        self.error('Writing pkt %s to pcap %s: %s' % (ptype, self.pcapdump[ptype], e))

    self.queue({'sensor': self.hostname,
                  'time': seentime,  'mac': src_mac,
                   'seq': seq,      'ssid': ssid,
                  'rssi': signal,  'ptime': pktime,
                 'ptype': ptype, 'dst_mac': dst_mac,
                 'frame': str(base.__class__),
               'channel': channel, 'version': self.version})

if __name__ == '__main__':
  listener = Listener()
  
  if len(sys.argv) > 1:
    action = sys.argv[1]

    if action == 'stop':
      listener.do_exit()
    elif action == 'restart':
      listener.restart()
  else:
    listener.start()
