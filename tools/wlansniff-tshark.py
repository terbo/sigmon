#!usr/bin/env python

import time, platform, pyshark

hostname = platform.node()
delim = ','
QR = lambda x:'"'+str(x)+'"'

def sniff_pyshark():
  capture = pyshark.LiveCapture(interface='mon0')
  capture.apply_on_packets(pktcb)
def pktcb(p):
  if p['wlan'].fc_type_subtype not in ('0x04'): return
  out = [hostname, time.time()]
  out.append(p['wlan'].ta)
  out.append(p['radiotap'].dbm_antsignal)
  out.append(p['wlan_mgt'].ssid)
  
  if out[-1] == 'SSID: ': out[-1] = ''

  print delim.join([QR(x) for x in out])
  
sniff_pyshark()
