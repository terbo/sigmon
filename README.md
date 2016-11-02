Originally Sigmon was designed to run from one computer, possibly with multiple wifi cards as input, and record as much as it could and do some analysis.

I am pleased to be soon releasing a new design which allows for multiple remote sensors to collaborate by various methods with a server, which can be separated from HTTP &amp; REST servers providing the interface to the large amount of collected data.

I am currently exploring the many options as to how this system can be put together, what it can be used for, and how to best expose others to it.

The current setup:

**Sensors**

*Hardware*:

    TP-Link Travel Routers (MR3020/3040)
    OpenWRT (Chaos Calmer) with 16GB USB Root
    TP-Link N USB with 7dBi ALFA Antenna
    

Also used are two linux laptops with ALFA Silver & Black adapters,
And 9dBi dipole and Cantenna antennas, respectively. The latter
sees the most probes, but needs some consideration to work in the
OpenWRT power constraints.

*Client*:

    Python script (~100 lines)
    Required Modules: Pcapy, Impacket, pid
    Also uses JSON & URLLib2

Client software is run on boot. A bash script sets monitoring mode.
A pcap capture loop is setup and redirected by HTTP JSON POST
to the REST server. 

The rest.py module uses Eve, and then validates the input,
submitting it to the MongoDB server.

**Database**:
*Hardware*:

    Intel Q720 laptop, 8x CPU with 4GB RAM
(Few years old, but fairly fast)

*Software*:

    MongoDB 3.2.1
    Debian Linux 8.3
    Python 2.7.9
    
*Sigmon module*:

*Required modules*: PyMongo, PyTZ, netaddr, humanize

sigmon.py does most of the work, ~800 lines of code to be rewritten

**Web Interface**:
    Required modules: Flask, Flask-Bootstrap

The views.py module is responsible for displaying the data.
It offers several JSON API endpoints, which may be moved into
the rest.py module, and provide various queries, data for graphing,
and ultimately the overview.html


Most of the past month has been spent on the above.

Prospectively, I am looking at various ways to display and visualize the copious amounts of data being collected.

    5 Minutes 4  sensors  655 probes  55 macs 11 vendors  18 ssids
    overall probes: 1,304,330 devices: 17,002 sessions: 462 vendors: 121 ssids: 2,589


     pp(probes_per_sensor(start=_now(UTC)-_hours(24),stop=24))
    [{u'_id': u'sensor1',
      u'avgrssi': -74.6542219397887,
      u'maxrssi': -94,
      u'minrssi': -29,
      u'probes': 12589},
     {u'_id': u'sensorb',
      u'avgrssi': -79.85067155401154,
      u'maxrssi': -98,
      u'minrssi': -2,
      u'probes': 36557},
     {u'_id': u'sensorj',
      u'avgrssi': -55.40700218818381,
      u'maxrssi': -74,
      u'minrssi': -7,
      u'probes': 18280},
     {u'_id': u'sensorz',
      u'avgrssi': -79.60670731707317,
      u'maxrssi': -97,
      u'minrssi': -27,
      u'probes': 51168}]


Thats on a monday. Weighting and long/lat are used to equalize this information with session entry/exit over time, possibly to be fed into a markov simulator fed to a neural net... oh my.


**Queries available**

Loading the main page, overview.html, displays:
    Selected time period/Overall collection statistics
    Daily/Hourly graphs of traffic, sessions, unique devices/unknown ouis, and SSID's probed for

Sortable table showing probe data for the selected period by MAC address, which is filterable in several ways:
    Frequency of appearance, vendor, proximity (RSSI), time, as well as overall data collected


**Essentially, with a few of my custom filters, I can take a list of 1000 unique devices and filter it down to 5 in a few clicks.**


Bootstrap is currently used for the interface, as well as [D3](https://github.com/d3/d3/wiki/Gallery) and LeafletJS, but I am looking into a more visual interface (and also mobile friendly) designed after some of these sites:

* [Matrix Admin](http://themedesigner.in/demo/matrix-admin/index.html)

* [ThreatWiki/Kenya](http://vast-journey-7849.herokuapp.com/kenyavisualization)

* [TaxiTracker](http://chriswhong.com/open-data/taxi-techblog-2-leaflet-d3-and-other-frontend-fun/)

I think a very nifty interface could be made with D3, but I might need some AngularJS to make it work properly. We'll see.

I'll be editing the code and publishing it in the next week, with some screenshots of the POC coming soon.

Oh, and if you want to help or have any questions, feel free, I need to figure out what to call this thing, and also how to explain it to people who have *no* idea what any of the above was about.

Previous version is available @ [0.9-prev branch](https://github.com/terbo/sigmon/tree/2.9-prev) 


See Also


Great Overview of network security past to future -
https://youtu.be/QjnEHbJ_UgM - Securing the Internet of Things in the enterprise


Sigmon Wiki - https://github.com/terbo/sigmon/wiki

Projects with a grander scope:

Snoopy - http://github.com/sensepost/snoopy-ng and https://github.com/sensepost/snoopy
Probr - http://probr.ch/
WiWo - https://n0where.net/802-11-massive-monitoring-wiwo/
CreepyDOL - http://blog.ussjoin.com/2013/08/creepydol.html and https://github.com/ussjoin



Videos:

http://www.youtube.com/watch?v=GvrB6S_O0BE - The Machines That Betrayed Their Masters by Glenn Wilkinson_
http://www.youtube.com/watch?v=ubjuWqUE9wQ - DEFCON 21 - Stalking a City for Fun and Frivolity
http://www.youtube.com/watch?v=NjuhdKUH6U4 - DEFCON 20 - Can You Track Me Now? Government And Corporate Surveillance Of Mobile Geo-Location




