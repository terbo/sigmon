#!/usr/bin/python

import sys, os, humanize, time
import threading
interval = 15
ifaces = []
packets = dict()

def _get_rx_pkts(iface):
	try:
		rxpkts = open('/sys/class/net/%s/statistics/rx_packets' % iface,'r')
		pkts = rxpkts.read()
		rxpkts.close()
		return pkts
	except Exception as inst:
		print 'Opening %s: %s' % (iface, inst)

def get_rx_pkts(iface):
	pkts1 = pkts2 = ''
	pkts1 = _get_rx_pkts(iface)
	time.sleep(interval)
	pkts2 = _get_rx_pkts(iface)
	packets[iface] = int(int(pkts2) - int(pkts1))

if len(sys.argv) <= 1:
	print 'Usage: %s [interface] [interface] ...' % sys.argv[0]
	print 'Measure the number of packets on a given (monitor) interface'
	print ''
	sys.exit(1)

print 'Reading', 

for i in range(1,len(sys.argv)):
	print '%s' % sys.argv[i],
	ifaces.append(sys.argv[i])

print 'every %s seconds\n' % interval

while True:
	threads = []
	for iface in ifaces:
		t = threading.Thread(target=get_rx_pkts,kwargs={'iface':iface},name=iface)
		threads.append(t)

	for t in threads:
		t.start()

	for t in threads:
		t.join()

	for iface in sorted(ifaces, cmp=lambda a,b: cmp(packets[b],packets[a])):
		pp = packets[iface]
		ppm = pp * 4
		pps = ppm / 60
		
		print '%s rx pp/pps/ppm: %s/%s/%s' % (iface, pp,pps, ppm)	

	print '-' * 15

'''
        R1=`cat /sys/class/net/$1/statistics/rx_packets`
        sleep $INTERVAL
        R2=`cat /sys/class/net/$1/statistics/rx_packets`
        RXPPS=`expr $R2 - $R1`
        echo "$1 RX: $RXPPS pkts/s"
done
'''
