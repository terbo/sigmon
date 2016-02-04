#!usr/bin/env python

import logging
from logging.handlers import RotatingFileHandler
logger = logging.getLogger('probes')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('probes.csv.bz2', encoding='bz2', maxBytes=5000000, backupCount=99999)
logger.addHandler(handler)

MAX_LEN      = 1514    # max size of packet to capture
PROMISCUOUS  = 1       # promiscuous mode?
READ_TIMEOUT = 100     # in milliseconds
PCAP_FILTER  = ''      # empty => get everything (or we could use a BPF filter)
MAX_PKTS     = -1      # number of packets to capture; -1 => no limit

import pcapy, impacket, binascii
import time, platform
from impacket import ImpactDecoder

hostname = platform.node()

RTD = ImpactDecoder.RadioTapDecoder()
delim=','
QR=lambda x:'"'+str(x)+'"'

def getBssid(arr):
  #Get Binary array to MAC addr format
  out = []
  s = binascii.hexlify(arr)
  t = iter(s)
  st = ':'.join(a+b for a,b in zip(t,t))
  return st

def sniff_pcapy():
  c = pcapy.open_live("mon0", MAX_LEN, PROMISCUOUS, READ_TIMEOUT)
  c.loop(-1, pcapy_packet)

def pcapy_packet(header, data):
  radio_packet = RTD.decode(data)
  signal = -(256-radio_packet.get_dBm_ant_signal())
  dot11 = radio_packet.child()
  
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

    out = [hostname, time.time()]
    try: ssid = str(base.get_ssid())
    except: ssid = ''
    out.append(getBssid(bssid_base.get_source_address()))
    out.append(signal)
    out.append(ssid)
    
    logger.info(delim.join([QR(x) for x in out]))

sniff_pcapy()
