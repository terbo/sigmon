sigmon
======

Display wireless probe requests like airodump-ng in python and scapy

This program displays wireless probe requests from associated and unassociated wireless clients in range.
The output is similar to that of airodump-ng from the aircrack-ng suit.

It will also play a sound when a new client is detected (the kismet sound, available @ http://goo.gl/oDi5sR) and can
be instructed to note familiar devices (favorites) such as machines you own.

Requirements
============

You will need a wireless card that is capable of going into <a href=http://en.wikipedia.org/wiki/Monitor_mode>monitor mode</a>, and is compatible with <a href=http://www.aircrack-ng.org/>aircrack</a>.

Only tested it on one machine! But it should work on others.

Also required are of course <b>python</b> and the <b>scapy</b> libraries, and also <b>netaddr</b> for mac address lookups.

The testing platform is <b>Kali Linux</b> 1.0.9 running on an i686 kernel version 3.14.<br>
The tested chipset was a realtek 8187.

Usage
=====

Running sigmon.py without any arguments will begin listening for probes from the default mon0 interface.
airmon-ng must be run prior to create the monitor interface from the wireless interface. Use -i to choose
another interface; only one is currently supported.

Use the -f flag to favorite all of your own devices, and note them in the display.<br>
E.g. sigmon.py -f 00:00:00:00:00:00

A tailable version will come soon; this will be vaguely different from a tshark one-liner.

<pre>
	-d		print debug to stdout (--debug)
	-f		add a mac to favorite list (--fav)
	-i		select interface (--interface)
</pre>

Examples
========
<pre>
root#kali pts/0-/root/code/sigmon] ./sigmon --print

 mon0 PKTS: 2297 [ Elapsed: 65 ][ 1413501263 ][ 8 Clients ][ 2 SSIDs ][ sorting by signal level

				Close Clients:

 STATION				PWR	Frames	Probes

				Farther clients:

 STATION				PWR	Frames	Probes

 34:23:ba:xx:xx:xx (Samsung E)		-75	2	[ANY]
 1c:99:4c:xx:xx:xx (Murata Ma)		-74	2	[ANY]
 30:19:66:xx:xx:xx (Samsung E)		-74	17	[ANY],linksys
 cc:9e:00:xx:xx:xx (Nintendo )		-75	2	NETGEAR
 00:ee:bd:xx:xx:xx (HTC Corpo)		-71	5	[ANY]
 34:4d:f7:xx:xx:xx (LG Electr)		-73	7	[ANY]
 1c:99:4c:xx:xx:xx (Murata Ma)		-75	1	[ANY]
 40:0e:85:xx:xx:xx (Samsung E)		-78	1	[ANY]
</pre>


Caveats
=======

Some wireless cards won't report correct signal levels<br>
Currently doesn't save any information<br>
Will fill your screen after 10000 packets or a couple dozen clients<br>
Can cause your cat to do weird things<br>

TODO
====

Add pretty printed numbers<br>
Add other output options, couchdb, sqlite, sqlachemy<br>
Add curses display :D<br>

Contact
=======

CB Terry - terry.chad@gmail.com / github.com/terbo

See Also
========

Projects with a grander scope:<br>
<br>
Snoopy - https://github.com/sensepost/snoopy-ng and https://github.com/sensepost/snoopy<br>
CreepyDOL - blog.ussjoin.com/2013/08/creepydol.html and https://github.com/ussjoin<br>

Videos:

https://www.youtube.com/watch?v=GvrB6S_O0BE The Machines That Betrayed Their Masters by Glenn Wilkinson_<br>
https://www.youtube.com/watch?v=ubjuWqUE9wQ - DEFCON 21 - Stalking a City for Fun and Frivolity<br>
https://www.youtube.com/watch?v=NjuhdKUH6U4 - DEFCON 20 - Can You Track Me Now? Government And Corporate Surveillance Of Mobile Geo-Location<br>

Future
======
[Redacted]
