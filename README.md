sigmon 0.9c
======

Display wireless probe requests like airodump-ng in python and scapy<br>

This program displays probe requests from wireless clients in range.<br>
The output is similar to that of airodump-ng from the aircrack-ng suit.<br>

It can also play a sound when a new client is detected (the kismet sound, @ http://goo.gl/oDi5sR)
and can be instructed to note familiar devices (favorites) such as machines you own.<br>

The code is released under the GPL2 license.

What it does
============

Nowadays radio waves are crowded with signals; indeed, nearly every person has a radio transmitter
on them; some people have several. These transmitters are personal cellular, wireless, and bluetooth
devices, and this program focuses on listening to the wireless signals.

Each time you connect to a wireless network and your device remembers the name, it indefinitally searches
for it, as long as wireless is turned on. The way it does this is by sending out 'probe' requests that
contain the name of the access point you are looking for, in the form of a service set identifer (<a href=http://en.wikipedia.org/wiki/SSID)>SSID</a>).
Also contained in this probe is your machine access control (<a href=http://en.wikipedia.org/wiki/MAC_Address>MAC</a>) address, which is completely unique to
your device.

These probes are sent into the airwaves unencrypted. What this means is that anyone listening for these
probes can (<b>a</b>) uniquely identify each device and (<b>b</b>) view what networks each device is looking for.
This program displays that information.

Also included in this information is a relative signal strength, which can be used to determine approximate
distance from the base station; with more base stations, finer granularity in location can be achieved.

While some percentage of people have smart phones, a smaller number have wireless always enabled.
Even so, the number of results this program shows can be used to form a demographic map.

Other uses for this data can be discovered; at the end of this file videos are linked that include some
of the wide ranging security implications.

The Requirements
============

You will need a wireless card that is capable of going into <a href=http://en.wikipedia.org/wiki/Monitor_mode>monitor mode</a>, and is compatible with <a href=http://www.aircrack-ng.org/>aircrack</a>.<br>

Only tested it on one machine, but it should work on others.<br>

Also required are of course <b>python</b> and the <b>scapy</b> libraries.<br>
Also, <b>netaddr</b> for mac address lookups, and <b>humanize</b> for pretty numbers.<br>

The testing platform is <b>Kali Linux</b> 1.0.9 running on an i686 kernel version 3.14.<br>
The tested chipsets were a realtek 8187 and an atheros ar9271.<br>

Usage
=====

Running sigmon.py without any arguments will begin listening for probes from the default mon0 interface. <br>
airmon-ng must be run prior to create the monitor interface from the wireless interface. <br>
Use -i to choose another interface; only one is currently supported. <br>

Use the -f flag to favorite all of your own devices, and note them in the display.<br>
E.g. sigmon.py -f 00:00:00:00:00:00 -f 00:00:00:00:00:01 <br>

Use sigmon.py -t to output a tailable csv version (all information on one line)

Use sigmon.py -l [number] to listen for a limited number of packets, then exit.
This is not the same as the number of well-formed wireless packets it will display.

<pre>
sigmon [interface] 
	-h		show this help 

	-f		add a mac to favorite list (--fav) 
	-i		select interface (--interface) 
	-l		stop after x number of packets (--limit) 
	-t		tailable output (--tail) 
	-d		print debug to stdout (--debug) 

version 0.9c 
</pre>

Examples
========
<pre>
root#kali pts/0-/root/code/sigmon] ./sigmon
 IF: mon0 18 probes [ Started: 10 seconds ago ][ 2014-10-17 23:28:48.117824 ][ 3 Clients ][ 1 SSIDs ][ sorting by last seen

				Close Clients:
 STATION					PWR	Probes

  50:cc:f8:6f:xx:xx  (Samsung Electro Me)	-34      5        [ANY]

				Farther clients:
 STATION					PWR	Probes

  7c:61:93:ad:xx:xx  (HTC Corporation   )	-74      9        NETGEAR01,[ANY]
  c4:43:8f:66:xx:xx  (LG Electronics    )	-73      4        [ANY]
</pre>

Caveats
=======

Some wireless cards won't report correct signal levels (some onboard laptop cards)<br>
Currently doesn't save any information (looking into couchdb)<br>
Will fill your screen after 10000 packets or a couple dozen clients<br>
Can cause your cat to do weird things<br> 

TODO
====

Add other output options, couchdb, sqlite, sqlachemy<br>
Add curses display :D<br>

Contact
=======

CB Terry - terry.chad@gmail.com / http://github.com/terbo

See Also
========

Projects with a grander scope:<br>
<br>
Snoopy - http://github.com/sensepost/snoopy-ng and https://github.com/sensepost/snoopy<br>
CreepyDOL - http://blog.ussjoin.com/2013/08/creepydol.html and https://github.com/ussjoin<br>

Videos:

http://www.youtube.com/watch?v=GvrB6S_O0BE - The Machines That Betrayed Their Masters by Glenn Wilkinson_<br>
http://www.youtube.com/watch?v=ubjuWqUE9wQ - DEFCON 21 - Stalking a City for Fun and Frivolity<br>
http://www.youtube.com/watch?v=NjuhdKUH6U4 - DEFCON 20 - Can You Track Me Now? Government And Corporate Surveillance Of Mobile Geo-Location<br>

Future
======
[Redacted]
