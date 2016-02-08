#!/usr/bin/env python
""" print sigmon pickle files to csv: pickle-to-csv .sigmon.p [sigmon.csv] """

from sigmon import *

def conftocsv(infile,outfile=False):
  try:
    conf = pickle.load(bz2.BZ2File(infile,'rb'))
  except:
    try:
      conf = pickle.load(open(infile,'rb'))
    except:
      pass

  clients = len(conf.c.keys())
  ssids = len(conf.ssids)
  vendors = len(conf.vendors)
  probes = conf.probes

  output = '#pickle-to-csv.py,sigmon version %s,%s probes,%s clients,%s ssids,%s vendors\n' % ( conf.version, probes, clients,
                                                                                                    ssids, vendors )
  output = 'mac,vendor,probes,firstseen,lastseen,minsig,maxsig,avgsig\n'

  for client in conf.c:
    seen = len(conf.c[client].seen)
    try: vendor = conf.c[client].vendor.replace(',',' ')
    except: vendor = 'UNKNOWN'
    ssids = ','.join(conf.c[client].ssids)

    output += '"%s","%s","%s","%s","%s","%s","%s","%s","%s"\n' % (client,vendor, seen, conf.c[client].firstseen,
                                                                  conf.c[client].lastseen, min(conf.c[client].signal),
                                                                  max(conf.c[client].signal), avg(conf.c[client].signal), ssids)
  if outfile:
    with open(outfile,'w') as out:
      out.write(output)
  else:
    print output

if len(sys.argv) < 2:
  print __doc__
  sys.exit(-1)
elif len(sys.argv) < 3:
  conftocsv(sys.argv[1])
else:
  conftocsv(sys.argv[1],sys.argv[2])
