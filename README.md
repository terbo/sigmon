sigmon 0.9i - Prototype
======

Display/Record wireless probes like airodump-ng with scapy/wireshark<br>

sigmon, or Signal Monitor, displays probe requests from wireless clients in range.<br>
The output is similar to that of airodump-ng from the aircrack-ng suit.<br>

sigmon can also play a sound when a new client is detected (the kismet sound, @ http://goo.gl/oDi5sR)
and can be instructed to note familiar devices (favorites) such as machines you own or observe regularly.<br>

TL;DR: The 802.11 Wireless networking stack is fairly insecure.

The code is released under the GPL2 license.

What it does
============

Nowadays radio waves are crowded with signals; indeed, nearly every person has a radio transmitter
on them; some people have several. These transmitters are personal cellular, wireless, and bluetooth
devices, and this program focuses on listening to their wireless signals.

Each time you connect to a wireless network and your device remembers the name, it indefinitally searches
for it, as long as your wireless is turned on. The way it does this is by sending out 'probe' requests that
contain the name of the access point you are looking for, in the form of a service set identifer (<a href=http://en.wikipedia.org/wiki/SSID)>SSID</a>).
Also contained in this probe is your machine access control (<a href=http://en.wikipedia.org/wiki/MAC_Address>MAC</a>) address, which is completely unique to your device.

These probes are sent into the airwaves unencrypted. What this means is that anyone listening for these
probes can (<b>a</b>) uniquely identify each device and (<b>b</b>) view what networks each device is looking for.
This program works with that data.

Also included in this information is a relative signal strength, which can be used to determine approximate
distance from the base station; with more base stations, finer granularity in location can be achieved.

While some percentage of people have smart phones, a smaller number have wireless always enabled.
Even so, the number of results this program shows can be used to form a demographic map.

Other uses for this data can be discovered; at the end of this file videos are linked that include some
of the wide ranging security implications.

The Requirements
============

You will need a wireless card that is capable of going into <a href=http://en.wikipedia.org/wiki/Monitor_mode>monitor mode</a>, and is compatible with <a href=http://www.aircrack-ng.org/>aircrack</a>.<br>

Required python libraries:

* pyshark and tshark/wireshark
* netaddr
* humanize
* ansi
* ansicolors

You can simply do "pip install -r requirements.txt --upgrade" to fetch the python modules.
(pyshark requires an updated lxml, gevent and trollius)

The testing platform is <b>Kali Linux</b> 1.0.9 running on an i686 kernel version 3.14.<br>
The tested chipsets were a realtek 8187 and an atheros ar9271.<br>

sigmon will probably work on most modern Linux distributions with python and airodump.
Has also been used successfully with several onboard (intel, etc) wireless cards.

Usage
=====

sigmon has (2) modes: a full screen mode, which is the default;
and a tail mode, which will print probes in csv format.

Edit the sigmon.cfg and choose your options. Running sigmon.py will begin
listening for probes. airmon-ng must be run <b>prior</b> to create the monitor
interface from the wireless interface. <br>

In-program help is available by striking the 'h' key.
<pre>
      space       display status
      s           choose sort method
      a           show access point list
      c           show client list
      f           filter clients
      \           search for mac or ssid
      /           highlight search
      G           display graphs [soon]
      T           show running threads
      A           add an interface
</pre>

Command line options:
<pre>
sigmon.py [options] [interface],...
          listen for wireless probe requests
           -h          show this help
      
           -p          mock curses display (default)
           -f          add a mac to favorite list (--fav [mac])
           -d          print debug to stdout, more for more info (--debug)
           -t          tailable (CSV) output (--tail)
           -P          disable saving of pickle file
           -q          quiet output (--quiet)
      
      version 0.9i
</pre>

The program will automatically save the configuration and seen clients to .sigmon.p every 5 minutes.

Examples
========
<pre>
  [ Started: 3 minutes ago ][ Mon Oct 27 21:42:22 2014 ][ 8 Clients ][ 8 SSIDs ][ 4 Vendors ][ sorted by vendor

	STATION						Signal	#Lost	#Probes	SSIDs
                                    Close Clients:

2  *5c:f9:38:xx:xx:xx (Apple, Inc / iPad         )	-42	0      76      [ANY]

                                   Farther Clients:

2   48:d7:05:xx:xx:xx  (Apple                     )	-86	2      98      netgear
2   b0:9f:ba:xx:xx:xx  (Apple                     )	-91	0      15      linksys
1   2c:41:38:xx:xx:xx  (Hewlett-Packard Company   )	-76	0      71      [ANY], default
0   cc:9e:00:xx:xx:xx  (Nintendo Co., Ltd.        )	-78	0      6       dlink

                                Recently Seen Clients:

1   44:4c:0c:xx:xx:xx  (Apple                     )	-73	0      12      [ANY]
1   4c:82:cf:xx:xx:xx  (Echostar Technologies     )	-72	0      1       [ANY]

                                     Loud Clients:

1  *78:ca:39:xx:xx:xx  (Apple / rocketbu          )	-80	1      174     
        McDonalds Free Wifi, Full O Beans, VCLibrary, Marriot


  sigmon 0.9h on mon0,mon1,mon2             2,026/80,852/4,072 probes/pkts/dropped                        [h]elp  [q]uit

> 
</pre>

Caveats
=======

Can cause your cat to do weird things<br> 
Newer wireless devices send out fake probes, and restrict broadcasting their entire preferred client list<br>

ANECDOTES
=========

So some of the things I have seen while watching the output of this program include phone numbers, birthdates, and even a social security number and an obvious password..<br>

BUGS
====

Innumerable

TODO
====

Total Rewrite

Contact
=======

CB Terry - http://github.com/terbo<br>

See Also
========

Sigmon Wiki - https://github.com/terbo/sigmon/wiki<br>
<br>
Projects with a grander scope:<br>
<br>
Snoopy - http://github.com/sensepost/snoopy-ng and https://github.com/sensepost/snoopy<br>
Probr - http://probr.ch/<br>
WiWo - https://n0where.net/802-11-massive-monitoring-wiwo/<br>
CreepyDOL - http://blog.ussjoin.com/2013/08/creepydol.html and https://github.com/ussjoin<br>

<br>Videos:

http://www.youtube.com/watch?v=GvrB6S_O0BE - The Machines That Betrayed Their Masters by Glenn Wilkinson_<br>
http://www.youtube.com/watch?v=ubjuWqUE9wQ - DEFCON 21 - Stalking a City for Fun and Frivolity<br>
http://www.youtube.com/watch?v=NjuhdKUH6U4 - DEFCON 20 - Can You Track Me Now? Government And Corporate Surveillance Of Mobile Geo-Location<br>

Future
======
[Redacted]
