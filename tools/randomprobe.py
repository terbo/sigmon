#!/usr/bin/python -u

from scapy.all import *
import os, sys
import threading

global ssids
ssids={}
global clients
clients={}

def ProbeAmplify(packet):
  try:
    src = packet.addr2
    if len(src):  clients[src] = True
    dst = packet.addr3
  except:
    return

  try:
    ssid = str(packet[Dot11Elt].info.decode('utf-8')[:32])
    ssid = re.sub('\n','',ssid)
    if len(ssid): ssids[ssid] = True
  except:
    return

  # from fakeap callbacks
  if len(packet.notdecoded[8:9]) > 0:
    flags = ord(packet.notdecoded[8:9])
    if flags & 64 != 0:
      return


  if len(clients) and len(ssids):
    for cl in clients:
      c = re.sub(':','-',cl)
      for s in ssids:
        print '.',
        #print '%s->%s, ' % (cl,s),
        t = threading.Thread(target=SendProbeReq,kwargs={'ssid':s,'src':cl}, name='probe'+c+s)
        t.start()

  else:
    #print 'Got %d clients %d ssids ... waiting for 6 and 5 ssids.\r' % (len(clients), len(ssids)),
    return

def SendProbeReq(ssid='',count=1,iface='mon2',src='00:00:00:00:00:00',dst='ff:ff:ff:ff:ff:ff'):
  mac = src

  param = Dot11ProbeReq()
  essid = Dot11Elt(ID='SSID',info=ssid)
  rates  = Dot11Elt(ID='Rates',info="\x03\x12\x96\x18\x24\x30\x48\x60")
  dsset = Dot11Elt(ID='DSset',info='\x01')
  pkt = RadioTap()\
    /Dot11(type=0,subtype=4,addr1=dst, addr2=mac, addr3=dst)\
    /param/essid/rates/dsset

  #print '[*] 802.11 Probe Request from %s: SSID=[%s], count=%d' % (mac, ssid,count)
  try:
    sendp(pkt,count=count, inter=0.1, verbose=0, iface='mon2')
  except:
    raise

  sys.exit(0)

sniff(prn=ProbeAmplify, iface=sys.argv[1], lfilter=lambda p: (Dot11ProbeReq in p))
