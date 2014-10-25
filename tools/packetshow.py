#! /usr/bin/env python

import sys
from scapy.all import *
import pprint

def showpkt(p):
	#if p: p.display()
	print pprint.PrettyPrinter(p)
	try:
		j = input('Press any key to continue')
	except:
		pass

sniff(prn=showpkt,iface=sys.argv[1])
