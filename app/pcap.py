##
#   pcap handeling
##

# save uploaded pcap blob to capture directory, then readcaps()
def savecap(filename, data):
  with open('%s/%s' % (SIGMON_PCAP, filename), 'wb') as capfile:
    capfile.write(data)
  
  readcaps()

# read pcap upload directory and initiate pcap reader
def readcaps():
  for pcap_file in glob('%s/*.cap' % SIGMON_PCAP):
    try:
      if int(time()) - os.stat(pcap_file)[7] > 10:
        readpcap(pcap_file)
    except:
      pass

# take a packet and add it to daily, hourly, then probes collections
def readpcap(pcap_file):
  bulk_probes = db.probes.initialize_unordered_bulk_op()

  sensor = re.sub(r'_.*',r'',os.path.basename(pcap_file))
  
  try:
    cap = pcapy.open_offline(pcap_file)
  except pcapy.PcapError, e:
    newfile = "%s/../errors/%s" % ( SIGMON_PCAP, os.path.basename(pcap_file) )
    error("Unable to read, moving %s to %s:" % (os.path.basename(pcap_file),os.path.dirname(newfile)))
    os.rename(pcap_file,newfile)
    return
 
  try:
    hdr = pkt = True
    
    while hdr and pkt:
      hdr,pkt = cap.next()
      if hdr and pkt:
        data = pcap_pktcb(sensor,hdr,pkt, sensor)
      else:
        raise
  except:
    # called functions should raise exceptions
    pass
  
  # need to either mergecap into reasonably sized pcaps or
  # archive in some other way
  if unsynced > 50:
    try:
      bulk_probes.execute()
    except BulkWriteError as bwe:
      debug('readcap(): bulk_probes: %s' % bwe.details)
    finally:
      unsynced = 0

  os.unlink(pcap_file)

def pcap_pktcb(sensor, hdr, pkt, source=False):
  try:
    radio_packet = RTD.decode(pkt)
    dot11 = radio_packet.child()

    if dot11.get_type() == impacket.dot11.Dot11Types.DOT11_TYPE_MANAGEMENT:
      base = dot11.child().child()
      
      if base.__class__ != impacket.dot11.Dot11ManagementProbeRequest:
        return

      try:
        pktime = dt.fromtimestamp(hdr.getts()[0]).strftime('%F %T')
        signal = -(256-radio_packet.get_dBm_ant_signal())
      except:
        return

      bssid_base = dot11.child()

      try: ssid = unicode(base.get_ssid())
      except: ssid = ''

      seq = bssid_base.get_sequence_number()
      mac = getBssid(bssid_base.get_source_address())
      
      return {
        'sensor': sensor,
        'mac':    mac,
        '_created':   dt.utcnow(),
        'time':   dt.utcnow(),
        'pktime': pktime,
        'ssid':   ssid,
        'rssi':   signal,
        'seq':    seq,
        'from':   source,
        'stats':  False,
       }

  except Exception as e:
    debug('pcap_pktcb(): %s' % e)
    pass

def getBssid(arr):
  #Get Binary array to MAC addr format
  try:
    s = binascii.hexlify(arr)
    t = iter(s)
    st = ':'.join(a+b for a,b in zip(t,t))
  except Exception as e:
    debug('getBssid(): error - %s' % e)
    pass
  return st
