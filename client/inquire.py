#!/usr/bin/env python
VERSION = '0.9-dev 0.051b'
# sigmon bluetooth scanner

# noice. now time to do oui resolution and
# class interpretation. but maybe offload it.

# --
# taken from query-with-rssi.py from Bluez
# and another simple script .. but if I
# didn't have to do two loops, it would seem
# more effecient. Though any device seen for
# less than two scans is probably less important.

# requires 0.22 or later (?) of bluez

import sys, os, time, resource
import datetime, logging, urllib3
from logging import debug, info, error
from pid import PidFile
from platform import node
from logging.handlers import RotatingFileHandler
import json,  signal, struct

import bluetooth
import bluetooth._bluetooth as bluez

class Sigmon():
  def __init__(self):
    self.version = VERSION

class Sensor(Sigmon):
  def __init__(self):
    Sigmon.__init__(self)

    self.starttime = time.time()

    self.debug   = os.environ.get('SIGMON_DEBUG', 1)
    self.apihost  = os.environ.get('SIGMON_APIHOST', '1.0.0.1')
    self.apiport  = os.environ.get('SIGMON_APIPORT', 8989)
    self.apibt  = os.environ.get('SIGMON_APIBT', '/bt/')
    self.homedir = os.environ.get('SIGMON_ROOT', '/data/sigmon')
   
    self.apiurls = {'bt': '%s' % ( self.apibt ) }
    
    self.logcsv = os.environ.get('SIGMON_CSVOUT', 0)
    self.logjson = os.environ.get('SIGMON_JSONOUT', 0)
    self.logweb = os.environ.get('SIGMON_WEBOUT',1)
    
    self.savelogs = os.environ.get('SIGMON_SAVELOGS',1)
    
    self.poststatus = os.environ.get('SIGMON_POSTSTATUS',1)
    
    self.statusurl = os.environ.get('SIGMON_STATSURL', '/logs.sensors/')
    
    self.iface = os.environ.get('BT_IDX', 0)
    self.queue_time = os.environ.get('QUEUE_TIME', 30)
    self.queue_packets = os.environ.get('QUEUE_PACKETS', 15)
    
    
    self.max_errors = 25
    self.statusprint = 60 * 7

    self.scriptname = os.path.basename(__file__).replace('.py','')
    self.hostname = node() 
    
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

    self.logfile = '%s/logs/%s.%s.%s-%s.log' % ( self.homedir,
                                           self.hostname,
                                           self.iface,
                                           self.scriptname,
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
    self.data = {
        'bt': []
    } 
    
    self.maxpoolsize = 1
    self.maxpooltimeout = None

    self.http_headers = urllib3.util.make_headers(keep_alive=True,
                                          user_agent='sigmon sensor %s' % self.version)
    self.http_headers.update({'Content-Type':'application/json'})

    self.pool = urllib3.HTTPConnectionPool(self.apihost, self.apiport,
                                      self.maxpoolsize,
                                      self.maxpooltimeout,
                                      headers=self.http_headers)
    
    debug('bt idx: %s ip: %s port %s endpoint %s' % \
        (self.iface, self.apihost, self.apiport, self.apibt))
    debug('sync: to web:%s csv:%s json:%s' % \
        (self.logweb, self.logcsv, self.logjson))
    
    info('syncing every %s seconds/%s packets)' % \
        (self.queue_time, self.queue_packets))

    signal.signal(signal.SIGINT, self.do_exit)
    
    self.pkts = 0
    self.active = False
    
  
  def error(self,err):
      error(err)
      self.errors += 1
      self.errorlog.append('%s %s' % (datetime.datetime.now().strftime('%F-%T'), err))

  def do_exit(self,arga,argb):
    if self.cease() and self.queued():
      error('Exiting, wrote %s packets to csv in %s' % (self.writecsv(), self.homedir))
    sys.exit(self.errors)

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
    
    if self.debug:
      info('uptime: %s' % self.last_status['uptime'])
      info('memory usage: %.2fmb' % (self.last_status['memusage']))
      info('synced: %d packets (%d errors)' % \
        ( self.synced, len(self.errorlog) ))
      info('queued: %s, last synced: %.2f seconds ago' % \
        (self.last_status['queued'], self.last_status['lastsync']))
    
    if self.poststatus:
      self.post(self.statusurl, data=self.last_status)
    
    return self

  def writecsv(self):
    written = 0
    with open('%s/csv/%s-%s-%s.csv' % (self.homedir, self.hostname, self.iface,
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
      # i dont save pcap here, thats written for each packet
      # could make it another queued data hash...
      for field in self.data.keys():
        if len(self.data[field]):
          if self.logweb:   self.post(self.apiurls[field],field=field)
          if self.logjson:  print(self.data[field])
          if self.logcsv:   self.writecsv()

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
                                         headers=self.http_headers, assert_same_host=False)
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

class Inquirer(Sensor):
  def __init__(self, iface=1):
    Sensor.__init__(self)
    self.max_responses = 50
    self.iface = iface
    self.duration = 5
    self.scan_result = {}
    self.sleep_time = 1

  def ask(self):
    self.active = True
    while self.active:
      try:
        self.scan_result = self.do_rssi_scan(self.iface,verbose=False)
      except Exception as e:
        self.error(e)
      finally:
        for dev in self.scan_result:
          self.queue({ 'ptype': 'bt', 'mac': dev[1], 'sensor': self.hostname,
                        'name': dev[2], 'devclass': dev[4], 'iface': self.iface,
                        'rssi': dev[3], 'time': dev[0] })
      # submit devices..
      time.sleep(self.sleep_time)
  def cease(self):
    self.active = False
    return self

  def printpacket(self,pkt):
    for c in pkt:
      sys.stdout.write("%02x " % struct.unpack("B",c)[0])
    print() 

  def read_inquiry_mode(self,sock):
    """returns the current mode, or -1 on failure"""
    # save current filter
    old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    # Setup socket filter to receive only events related to the
    # read_inquiry_mode command
    flt = bluez.hci_filter_new()
    opcode = bluez.cmd_opcode_pack(bluez.OGF_HOST_CTL, 
        bluez.OCF_READ_INQUIRY_MODE)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    bluez.hci_filter_set_event(flt, bluez.EVT_CMD_COMPLETE);
    bluez.hci_filter_set_opcode(flt, opcode)
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

    # first read the current inquiry mode.
    bluez.hci_send_cmd(sock, bluez.OGF_HOST_CTL, 
        bluez.OCF_READ_INQUIRY_MODE )

    pkt = sock.recv(255)

    status,mode = struct.unpack("xxxxxxBB", pkt)
    if status != 0: mode = -1

    # restore old filter
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
    
    return mode

  def write_inquiry_mode(self, sock, mode):
    """returns 0 on success, -1 on failure"""
    # save current filter
    old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    # Setup socket filter to receive only events related to the
    # write_inquiry_mode command
    flt = bluez.hci_filter_new()
    opcode = bluez.cmd_opcode_pack(bluez.OGF_HOST_CTL, 
        bluez.OCF_WRITE_INQUIRY_MODE)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    bluez.hci_filter_set_event(flt, bluez.EVT_CMD_COMPLETE);
    bluez.hci_filter_set_opcode(flt, opcode)
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

    # send the command!
    bluez.hci_send_cmd(sock, bluez.OGF_HOST_CTL, 
        bluez.OCF_WRITE_INQUIRY_MODE, struct.pack("B", mode) )

    pkt = sock.recv(255)

    status = struct.unpack("xxxxxxB", pkt)[0]

    # restore old filter
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )
    if status != 0: return -1
    return 0

  def device_inquiry_with_with_rssi(self, sock,verbose=False):
    # save current filter
    old_filter = sock.getsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    # perform a device inquiry on bluetooth device #0
    # The inquiry should last 8 * 1.28 = 10.24 seconds
    # before the inquiry is performed, bluez should flush its cache of
    # previously discovered devices
    flt = bluez.hci_filter_new()
    bluez.hci_filter_all_events(flt)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, flt )

    cmd_pkt = struct.pack("BBBBB", 0x33, 0x8b, 0x9e, self.duration, self.max_responses)
    bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY, cmd_pkt)

    results = []

    done = False
    
    while not done:
      pkt = sock.recv(255)
      ptype, event, plen = struct.unpack("BBB", pkt[:3])
      if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
        pkt = pkt[3:]
        nrsp = bluetooth.get_byte(pkt[0])
        for i in range(nrsp):
          addr = bluez.ba2str( pkt[1+6*i:1+6*i+6] )
          rssi = bluetooth.byte_to_signed_int(
              bluetooth.get_byte(pkt[1+13*nrsp+i]))
          devclass_raw = struct.unpack ("BBB",
                  pkt[1+8*nrsp+3*i:1+8*nrsp+3*i+3])
          devclass = (devclass_raw[2] << 16) | \
                 (devclass_raw[1] << 8) | \
                 devclass_raw[0]
          try:
            name = bluetooth.lookup_name(addr)
          except:
            name = 'unknown'
          time = datetime.datetime.now().isoformat()
          results.append( [time, addr, name, rssi, devclass] )
          if verbose:
            print("%s,%s,%s,%s,%s" % (time,addr,name, rssi, devclass))
      elif event == bluez.EVT_INQUIRY_COMPLETE:
        done = True
      elif event == bluez.EVT_CMD_STATUS:
        status, ncmd, opcode = struct.unpack("BBH", pkt[3:7])
        if status != 0:
          print("uh oh...")
          printpacket(pkt[3:7])
          done = True
      elif event == bluez.EVT_INQUIRY_RESULT:
        pkt = pkt[3:]
        nrsp = bluetooth.get_byte(pkt[0])
        for i in range(nrsp):
          addr = bluez.ba2str( pkt[1+6*i:1+6*i+6] )
          results.append( ( addr, -1 ) )
          if verbose:
            print("[%s] (no RRSI)" % addr)
      else:
        print("unrecognized packet type 0x%02x" % ptype)
      if verbose:
        print("event ", event)

    # restore old filter
    sock.setsockopt( bluez.SOL_HCI, bluez.HCI_FILTER, old_filter )

    return results

  def do_rssi_scan(self, dev_id,verbose=False):
    if verbose:
      print 'Using device %d' % dev_id

    try:
      sock = bluez.hci_open_dev(dev_id)
    except:
      print("error accessing bluetooth device...")
      return 0

    try:
      mode = self.read_inquiry_mode(sock)
    except Exception as e:
      print("error reading inquiry mode.  ")
      print("Are you sure this a bluetooth 1.2 device?")
      print(e)
      sys.exit(1)
    
    if verbose:
      print("current inquiry mode is %d" % mode)

    if mode != 1:
      #print("writing inquiry mode...")
      try:
        result = self.write_inquiry_mode(sock, 1)
      except Exception as e:
        print("error writing inquiry mode.  Are you sure you're root?")
        print(e)
        sys.exit(1)
      if result != 0:
        print("error while setting inquiry mode")
        return 0

      if verbose:
        print("result: %d" % result)

    return self.device_inquiry_with_with_rssi(sock,verbose)

if __name__ == '__main__':
  inquirer = Inquirer()
  inquirer.ask()
