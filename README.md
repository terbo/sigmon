sigmon
======

Display wireless probe requests like airodump-ng in python and scapy

This program displays wireless probe requests from associated and unassociated wireless clients in range.
The output is similar to that of airodump-ng from the aircrack-ng suit.

It will also play a sound when a new client is detected (the kismet sound, available @ http://goo.gl/oDi5sR) and can
be instructed to note familiar devices (favorites) such as machines you own.

Requirements
============

You will need a wireless card that is capable of going into monitor mode, and is compatible with aircrack.
I have only tested it on one machine! But it should work on others

Also required are of course python and the scapy libraries, and also netaddr for mac address lookups.

The tested platform is Kali Linux 1.0.9 running on kernel 3.14.

Options
=======

<pre>
	-d		print debug to stdout (--debug)
	-f		add a mac to favorite list (--fav)
	-i		select interface (--interface)
</pre>

Examples
========
<pre>
root#kali pts/0*/root/code/sigmon] ./sigmon --print

 PKTS: 2297 [ Elapsed: 65 ][ 1413501263 ][ 8 Clients ][ 3 SSIDs ][ sorting by signal level

				Close Clients:

 STATION				PWR	Frames	Probes

				Farther clients:

 STATION				PWR	Frames	Probes

 34:23:ba:xx:xx:xx (Samsung E)		-75	2	[ANY]
 1c:99:4c:xx:xx:xx (Murata Ma)		-74	2	[ANY]
 30:19:66:xx:xx:xx (Samsung E)		-74	17	[ANY],linksys,default
 cc:9e:00:xx:xx:xx (Nintendo )		-75	2	NETGEAR
 00:ee:bd:xx:xx:xx (HTC Corpo)		-71	5	[ANY]
 34:4d:f7:xx:xx:xx (LG Electr)		-73	7	[ANY]
 1c:99:4c:xx:xx:xx (Murata Ma)		-75	1	[ANY]
 40:0e:85:xx:xx:xx (Samsung E)		-78	1	[ANY]

</pre>

Future
======
[Redacted]
