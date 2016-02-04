#!/usr/bin/env python
""" print sigmon pickle files to csv: pickle-to-csv .sigmon.p [sigmon.csv] """

from glob import glob
from sigmon import *
import random
from string import ascii_lowercase as asciimap

def conftocsv(infile,outfile=False):
  try:
    conf = pickle.load(bz2.BZ2File(infile,'rb'))
  except:
    try:
      conf = pickle.load(open(infile,'rb'))
    except:
      return

  clients = len(conf.c.keys())
  ssids = len(conf.ssids)
  vendors = len(conf.vendors)
  probes = conf.probes

  output = '#pickle-to-csv.py [%s],sigmon version %s,%s probes,%s clients,%s ssids,%s vendors\n' % ( conf.version, infile, probes, clients,
                                                                                                    ssids, vendors )
  output += 'mac,vendor,totalprobes,firstseen,lastseen,minsig,maxsig,avgsig\n'

  ssidz = set()
  for client in conf.c:
    #seen = len(conf.c[client].seen)
    #try: vendor = conf.c[client].vendor.replace(',',' ')
    #except: vendor = 'UNKNOWN'
    #try: ssids = ','.join(conf.c[client].ssids)
    #except: continue
#"ko","1454198625.8","98:f1:70:99:51:d4","-20","Beacon"

    ssids = ''
    ssid = ''

    for x in xrange(len(conf.c[client].signal)):
      t = conf.c[client].seen[x]
      s = conf.c[client].signal[x]
      
      if ( len(ssids) < 1 ) and ( len(conf.c[client].ssids) > 1 ):
        ssids = conf.c[client].ssids
        random.shuffle(ssids)
        ssid = ssids.pop(0)
      #elif len(conf.c[client].ssids) > 1:
      #  ssid = ssids.pop()
      #else:
      
      n = 0
      if ssid and len(ssid):
        for c in ssid:
          if c not in asciimap:
            n += 1
        if n >= 2:
          continue
      if ssid == None: ssid = ''

      print '"%s", "%s", "%s", "%s", "%s"' % ( infile, t, client, s, ssid )
    #output += '"%s","%s","%s","%s","%s","%s","%s","%s","%s"\n' % (client,vendor, seen, conf.c[client].firstseen,
    #                                                              conf.c[client].lastseen, min(conf.c[client].signal),
    #                                                              max(conf.c[client].signal), avg(conf.c[client].signal), ssids)
  #if outfile:
  #  with open(outfile,'w') as out:
  #    out.write(output)
  #else:
  #  print output.encode('ascii',errors='ignore'),

if len(sys.argv) < 2:
  print __doc__
  sys.exit(-1)
elif len(sys.argv) > 1:
  for f in sys.argv:
    conftocsv(f)
#else:
#  conftocsv(sys.argv[1],sys.argv[2])
