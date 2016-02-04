#!/usr/bin/env python
""" print sigmon pickle files to csv: pickle-to-csv .sigmon.p [sigmon.csv] """

from glob import glob
from sigmon import *

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

  output = '#pickle-to-json.py [%s],sigmon version %s,%s probes,%s clients,%s ssids,%s vendors\n' % ( conf.version, infile, probes, clients,
                                                                                                    ssids, vendors )
  #output += 'mac,vendor,totalprobes,firstseen,lastseen,minsig,maxsig,avgsig\n'

  for client in conf.c:
    seen = len(conf.c[client].seen)
    try: vendor = conf.c[client].vendor.replace(',',' ')
    except: vendor = 'UNKNOWN'
    try: ssids = ','.join(conf.c[client].ssids) # reused
    except: continue

    for x in xrange(conf.c[client].seen):
      what
      #out = {'mac': client, 'probes': seen, 'firstseen': firstseen, 'lastseen': lastseen, 
    
    output += '"%s","%s","%s","%s","%s","%s","%s","%s","%s"\n' % (client,vendor,
  if outfile:
    with open(outfile,'w') as out:
      out.write(output)
  else:
    print output.encode('ascii',errors='ignore'),

if len(sys.argv) < 2:
  print __doc__
  sys.exit(-1)
elif len(sys.argv) < 3:
  for f in glob('.sigmon*'):
    conftocsv(f)
else:
  conftocsv(sys.argv[1],sys.argv[2])
