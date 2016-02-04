#!usr/bin/env python

import time
import platform
from scapy.all import sniff, Dot11, Dot11Elt

delim = ','
QR = lambda x: '"'+str(x)+'"'
hostname = platform.node()

def pktcb(p):
  if (p.haslayer(Dot11) and p.type == 0 and p.subtype == 4):
    try:
      out = [hostname, time.time()]
      out.append(p.addr2[:32]) # mac
      out.append(str(-(256-ord(p.notdecoded[-4:-3])))) # signal
      out.append(p[Dot11Elt].info.decode('utf-8')[:32]) # ssid
      out = delim.join([QR(x) for x in out])
      print(out)
    except:
      pass

sniff(iface='mon0', store=0, prn=pktcb)
