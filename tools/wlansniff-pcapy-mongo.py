#!usr/bin/env python

""" catch all exceptions """
MAX_LEN      = 1514    # max size of packet to capture
PROMISCUOUS  = 1       # promiscuous mode?
READ_TIMEOUT = 100     # in milliseconds
PCAP_FILTER  = ''      # empty => get everything (or we could use a BPF filter)
MAX_PKTS     = -1      # number of packets to capture; -1 => no limit

import pcapy, impacket, binascii
import time, platform, pymongo

from impacket import ImpactDecoder
from pymongo.collection import ReturnDocument

hostname = platform.node()

mongo = pymongo.MongoClient(host='dv8')
db = mongo.sigmon

ssid_db = db.ssids
probe_db = db.probes
client_db = db.clients
last_synced = time.time()
sync_time = 60
datas = []

RTD = ImpactDecoder.RadioTapDecoder()
delim=','
QR=lambda x:'"'+str(x)+'"'

def sync(data):
  try:
    client = client_db.insert_one( {'mac': data['mac'],
                                    'ssid': data['ssid'],
                                    'drone': data['drone'],
                                    'time': data['time'],
                                    'signal': data['signal']
                                 })
    last_synced = time.time()
  except Exception as e:
    pass

def getBssid(arr):
  #Get Binary array to MAC addr format
  out = []
  s = binascii.hexlify(arr)
  t = iter(s)
  st = ':'.join(a+b for a,b in zip(t,t))
  return st

def sniff_pcapy():
  while True:
    try:
      c = pcapy.open_live("mon0", MAX_LEN, PROMISCUOUS, READ_TIMEOUT)
      c.loop(-1, pcapy_packet)
    except Exception as e:
      pass

def pcapy_packet(header, data):
  global datas
  
  radio_packet = RTD.decode(data)
  signal = -(256-radio_packet.get_dBm_ant_signal())
  dot11 = radio_packet.child()
  
  data = {}

  if dot11.get_type() == impacket.dot11.Dot11Types.DOT11_TYPE_DATA:
    return
    base = dot11.child()
    ip  = getBssid(base.get_address1())
    client = getBssid(base.get_address3()) 
    bssid = getBssid(base.get_address2())
    print 'Data:', channel, signal, bssid, ip, client

  elif dot11.get_type() == impacket.dot11.Dot11Types.DOT11_TYPE_MANAGEMENT:
    base = dot11.child().child()
    if base.__class__ != impacket.dot11.Dot11ManagementProbeRequest: return
    
    bssid_base = dot11.child()

    try: ssid = str(base.get_ssid())
    except: ssid = ''
    
    data['time'] = datetime.datetime.utcfromtimestamp(time.time())
    data['drone'] = hostname
    data['mac'] = getBssid(bssid_base.get_source_address())
    data['ssid'] = ssid
    data['signal'] = signal
   
    datas.append(data)

    if time.time() - last_synced > sync_time and len(datas) > 1:
      sync(datas)
      datas = []

sniff_pcapy()
