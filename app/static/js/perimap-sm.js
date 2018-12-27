// leaflet haetmap
// leaflet indoors
// time series
// history
// quadtree

//////////////////////////
// Map Functions
//
//

function delMarker() {
  var oldmark = S.markers.pop()
  if ( typeof(oldmark) !== 'undefined')
    S.map.removeLayer(oldmark)
}

function addMarker(ll, title, desc, radius, img, layer) {
  
  if ( typeof(img) !== 'undefined')
    S.maps.trackIcon = L.icon({
      iconUrl: '/static/img/'+img+'.jpg',
      iconSize:     [18, 22]})
      
  var marker = L.marker(ll,{ title: title,
                             icon: S.maps.trackIcon,
                             draggable: false,
                             riseOnHover: true})
  marker.bindPopup(desc)
  
  S.markers.push(marker)
  
	if ( typeof(layer) === 'undefined')
		marker.addTo(S.map)
	else
		return marker
}

function addLocated(mac, ll, rssi, locations) {
  //console.table([mac, ll[0], ll[1]])
  

  $.ajax({url: '/api/lookup/' + mac,
            type: 'GET', success: function(d) {
              if(S.locmarks.hasOwnProperty(mac)) {
                //console.log('Seen before')
                if(S.locmarks[mac].hasOwnProperty('marker') && S.locmarks[mac].marker != '')
                  S.locmarks[mac].marker.removeFrom(S.maps.track)
                
                S.locmarks[mac].loc.push(ll)
                S.locmarks[mac].lastseen = new Date()

              } else {
                //console.log('New device')
                S.locmarks[mac] = { loc: [ll],
                                    lastseen: new Date(),
                                    rssi: rssi,
                                    marker: '',
                                  }
              }


              S.locmarks[mac].data = d.data[mac]
              S.locmarks[mac].vendor = d.data[mac].info[0].vendor || 'Unknown'
              S.locmarks[mac].firstseen = d.data[mac].info[0].firstseen
              S.locmarks[mac].tags = d.data[mac].info[0].tags
              S.locmarks[mac].seenby = d.data[mac].info[0].sensors
              S.locmarks[mac].ssids = d.data[mac].info[0].ssids
              
              marker = L.circleMarker(ll,{
                                         title: mac.substr(0,4) + '(' + rssi + ')',
                                         color: 'red',
                                         radius: 6,
                                         draggable: false,
                                         riseOnHover: true})
              
              marker.bindPopup('MAC: ' + '<a target=_new href="/lookup/mac/' + mac + '">' + mac + '</a>  - <u>' +
                               S.locmarks[mac].vendor + '</u> - ' + 'RSSI: <b><i>' + rssi + '</i></b>dBm<br><br>' +
                               'Last Seen: ' + S.locmarks[mac].lastseen + '<br>' +
                               'First Seen: ' + S.locmarks[mac].firstseen + '<br><br>' +
                               'Tags: ' + JSON.stringify(S.locmarks[mac].tags) + '<br>' +
                               'SSIDS: ' + JSON.stringify(S.locmarks[mac].ssids))

              marker.addTo(S.maps.track)
              
							locations.forEach(function(e) {
								l = L.latLng([e[0][0], e[0][1]])
                console.log(l)
                L.circle(l, { radius: rssiToMeters(e[1]), opacity: .7, fillColor: 'lightgreen' }).addTo(S.maps.track)
							})
              
							S.locmarks[mac].marker = marker
       }
  })

  Object.keys(S.locmarks).forEach(function(mac) {
    if(S.locmarks[mac].lastseen < new Date(new Date() - (1000 * 150))) {
      S.locmarks[mac].marker.removeFrom(S.maps.track)
      //delete S.locmarks[mac]
    }
  })

}

function drawMap() {
  if ( ! $('#perimap').length )
    return
   
  if ( ! S.hasOwnProperty('maps') )
    console.log('Drawing Leaflet map')
    S.maps =  {version: 0.4,
               sensors: [],
               btn: {},
               centerTrack: true,
               circle: [],
               history: [],
               weights: {}
              }
  if ( ! S.hasOwnProperty('markers') )
    S.markers = []
  
  if ( ! S.hasOwnProperty('tracking') )
    S.tracking = []

 
  S.maps.terrainmap = L.tileLayer('https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.{ext}', {
      attribution: 'Map tiles by <a href="https://stamen.com">Stamen Design</a>, <a href="https://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> &mdash; Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      subdomains: 'abcd',
      minZoom: 0,
      maxZoom: 18,
      ext: 'png'
    })

  S.maps.osmap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
     { minZoom:1,maxZoom:19,
     attribution: "Map data &copy; <a href='https://openstreetmap.org'>OpenStretMap</a> contributors"})

  S.maps.gmap = L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                            { attribution: 'Map data &copy; <a href="http://maps.google.com">Google Maps</a>',
                             maxZoom: 20, subdomains:['mt0','mt1','mt2','mt3'] })

  S.maps.tiles = {'google': S.maps.gmap,
                  'terrain': S.maps.terrainmap,
                  'openstreetmaps': S.maps.osmap }
  
  S.totalprobes = 0
   
  S.maps.track = L.layerGroup()
  S.sensorll = {}

  S.maps.historyIcon = L.divIcon({className: 'fa fa-mobile'})
  S.maps.wificon = L.divIcon({className: 'fa fa-wifi'})

  S.map = L.map('perimap', {
    center: [ 35.3384971 , -118.9893678 ],
      zoom: 13,
      layers: [ S.maps.gmap ],
      renderer: L.svg()
  })
  
  S.maps.popup = L.popup()

  S.map.on('locationfound',mapLocated)


  S.maps.lc = L.control.locate({
    position: 'topright',
    //setView: 'always',
    drawCircle: true,
    metric: false,
    strings: {
        title: 'I am where? Take me there!'
    }
  }).addTo(S.map);
  
  S.maps.btn.gohome = L.easyButton('fa-home',
           function(btn, map) { S.map.flyToBounds(S.maps.bounds) },
           { position: 'topleft' })
  
	S.maps.btn.tracking = L.easyButton('fa-arrows',
           function(btn, map) { toggleTracking() } )

  S.maps.btn.locatable = L.easyButton('fa-wifi',
           function(btn, map) { toggleLocating() } )

  $.each(S.maps.btn, function(i){
    S.maps.btn[i].addTo(S.map)
  })
 	
  mapSensors()

  S.maps.layers = { sensors: S.maps.sensors,
                    coverage: S.maps.coverage,
                    tracks: S.maps.track,
                    //drawings: S.maps.drawnItems,
                  }
  

  L.control.fullscreen({
    position: 'topright',
    title: 'Fullscreen',
    titleCancel: 'Exit Fullscreen',
    forceSeparateButton: true,
  }).addTo(S.map);

  S.maps.control = L.control.layers(S.maps.tiles, S.maps.layers)
  S.maps.control.options.position = 'bottomright'
  S.maps.control.addTo(S.map)
  
  S.map.on('zoomend', mapZoomed)

  L.control.scale().addTo(S.map);

  S.maps.tracking = 0
  S.maps.locating = 0

  S.map.whenReady(mapReady)
}

function mapSensors() {
  if ( typeof S != 'undefined')
    if ( typeof S != 'undefined')
      if ( typeof S.sensors != 'undefined') {
        console.log('Astro Peemp!')
        S.totalprobes = 0
        for ( var sens in S.sensors ) {
          sensor = S.sensors[sens]
          if ( ! sensor.status.connected ) {
            continue
          }

          if(!sensor.hasOwnProperty('longlat'))
            continue
          
          var ll = L.latLng(sensor.longlat.coordinates)

          S.totalprobes += sensor.status.probes
          S.maps.weights[sens] = sensor.status.probes

          var sMarker = L.marker(ll, {className: 'sensor-'+sensor,
                                      title: sensor.name, riseOnHover: true,
                                    draggable: false, icon: S.maps.wificon})
            sMarker.bindPopup(sens + ' - ' + sensor.longlat.orientation + '(' + sensor.status.probes + ')')
        
				S.sensorll[sens] = ll

        S.maps.sensors.push(sMarker)
      }
 
      try {
        if(S.maps.hasOwnProperty('coverage'))
          S.maps.coverage.clearLayers()
        if(S.maps.hasOwnProperty('sensors'))
          S.maps.sensors.clearLayers()
      } catch (e) { console.log(e)}
      
      S.maps.circles = []

      Object.keys(S.maps.weights).forEach(function(d) {
        var probes = S.maps.weights[d]

                // just need the long / lat ...
        weight = (probes * 2) / S.totalprobes
        weight += weight < .2 ? .2 : 0

        S.maps.circles.push( L.circle(S.sensorll[d], {
                        className: d,
                        weight: weight * 3,
                        fillColor: 'lightblue',
                        radius: 9,
                        fillOpacity: weight * .3,
                        opacity: .1,
                        }))
     }) 
      
     S.maps.coverage = L.layerGroup(S.maps.circles)
     S.maps.sensors = L.layerGroup(S.maps.sensors)

     S.maps.sensors.addTo(S.map)
     S.maps.coverage.addTo(S.map)

     //setInterval('mapSensors()',30000)
  }
}

function resizeMarkers() {
  var m = S.currentZoom / 2

  //console.log('Current zoom level(half): ' + m)
  
  //S.maps.wificon = L.divIcon({fontSize: m + 15, iconSize: [m + 15, m + 15], className: 'fa fa-wifi'})
  
  /*S.sensors.forEach(function(d) {
    d._icon.remove()
    d.setIcon( S.maps.wificon )*/
}

function mapZoomed() {
  S.currentZoom = S.map.getZoom()
  
  $('i#zoomlevel').html(S.currentZoom)
  resizeMarkers()
}

function mapReady() {
  resizeMap()
  
  if( typeof S == 'undefined' || typeof S.sensors == 'undefined') {
    console.log('Waiting for sensors...')
    setTimeout('mapReady()',1500)
    return
  }
  console.log('Executing mapReady')

  S.maps.bounds = L.latLngBounds(S.sensors.wrt1.longlat.coordinates,
                                 S.sensors.timer.longlat.coordinates)
  try {
    S.map.locate({
      watch: false,
      locate: true,
      setView: true,
      enableHighAccuracy: true,
    })
  } catch (e) {
    console.log('No Location Available/Access Denied')
  }
  
  try {
    S.map.flyToBounds(S.maps.bounds)
  } catch(e) {
    console.log('No bounds?')
    console.log(e)
    S.map.flyTo(S.map.getCenter())
  }
}

function mapLocated(d) {
    S.maps.history.push({loc: d.latlng, time: d.timestamp, acc: d.accuracy})
    
    if ( S.maps.history.length > 1 )
      S.maps.track.addLayer(L.polyline([S.maps.history[S.maps.history.length - 2].loc, d.latlng],
                           { noClip: true, color: 'blue',
                             opacity: .6, weight: 2,
                             fillColor: 'purple',
                             fillOpacity: .3}))
  
    //if ( S.maps.centerTrack )
    // S.map.flyTo(d.latlng)
}

function drawDialog() {
  var html = ['<div class="container" style="background-color: white><table class="table-responsive">']
  Object.keys(S.locmarks).forEach(function(l) {
    html.push(('<tr><td>'+l.substr(0,5)+'</td><td>'+S.locmarks[l].rssi+'</tr>'))
  })

  html.push('</table></div>')

  my = parseInt($(S.map._container).css('height')) / 4 
  mx = parseInt($(S.map._container).css('width')) / 4 
  
	if(typeof S.dialog != 'undefined') {
    S.dialog.setSize([mx,my])
    S.dialog.setLocation([45,45])
	  S.dialog.setContent(html.join(''))
    return
  }
	
  S.dialog = L.control.dialog({size:[my,mx], minSize: [50,30],anchor:[20,20]})
           .setContent(html.join(''))
           .addTo(S.map)
  $('div.leaflet-control-dialog').css('background','rgba(100,100,100,.6)')
}

function mapPop(content,onto,timeout) {
  if (typeof onto === 'undefined')
    onto = new L.latLng(S.map.options.center)

  S.maps.popup.setLatLng(onto).setContent(content).openOn(S.map)
}

function findRange(loc) {
  if (! S.map.hasLayer(S.maps.coverage) ) {
    S.map.addLayer(S.maps.coverage)
  }

  S.maps.coverage.eachLayer(function(circle) {
    var bounds = circle.getBounds()
    console.log('Checking ' + loc + ' in range of ' + bounds)

    if ( ! bounds.contains(loc) ) {
      console.log(loc + ' out of bounds of ' + circle.options.className)
      Object.keys(S.maps.sensors).forEach(function(sensor) {
        if ( S.maps.sensors[sensor].options.title === circle.options.className )
          while(!bounds.contains(loc)) {
            circle.setRadius(circle.getRadius() + 1)
            bounds = circle.getBounds()
          }
      })
    }
  })
}

function resizeMap() {
  console.log('map resize')

  if ( S.maps.hasOwnProperty('bounds'))
    S.maps.bounds = S.map.getSize()

  setTimeout(function(){ S.map.invalidateSize()}, 350 + (Math.random() * 100))
}

  // try and draw a circle from the points given as sensors?
  // or focus to the center of all drawn objects

  // how about have it request sensors location over REST


// historcal layer ...
function drawTrack(data) {
	mac = data.mac
	loc = L.latLng(data.location.coordinates[0])

	if(S.hasOwnProperty('tracking') && S.tracking.length >= 2) {
		lastloc = S.tracking[S.tracking.length - 1].loc
		
		if(lastloc === loc)
			return
		
		//try { console.log(getDistance(loc, lastloc)) }
		//catch (e) { console.log('New device') }
		//if ( getDistance(loc, lastloc) < 5) { }
		console.log(lastloc + ' <-> ' + loc)
		
		console.log('Adding line')
		line = L.polyline([loc, lastloc])
	/*	,
							 { noClip: true, color: 'blue',
								 opacity: .6, weight: 2,
								 fillColor: 'purple',
								 fillOpacity: .3}) */
		
		console.log('Drawing line')
		line.addTo(S.maps.track)
		console.log('Line Drawn.')
	}
  
	S.tracking.push({mac: data.mac, loc: loc, data: data})


	// if lastloc < 4ft
  
  var html = '<h3>'+ mac + ' [' + loc.lat + ', ' + loc.lng + ']' + '</h3>'
  
  //if ( S.map.hasLayer('info') )
  //  S.map.removeLayer(S.maps.info)
  
  //S.maps.info = L.marker([S.maps.bounds.x,S.maps.bounds.y],
   //                          { icon: L.divIcon({ className: "labelClass", html: html })} )
  //S.maps.info.addTo(S.map)
  
  console.log('Adding Marker')
	delMarker()
	addMarker(loc, mac, html, 10, 'google-orangeguy', true).addTo(S.maps.track)
  //console.log('Finding Range')
	//findRange(loc)
}

function track(mac) {
  mapPop(mac)
  addTimer('track',"getTrack('"+mac+"')", 10)
}

function getOwn() {
  $.ajax({ url:'/api/owndevs',
           type: 'GET',
           success: function(data) {
                      S.devs = data.data
                      my = parseInt($(S.map._container).css('height')) / 2 
                      mx = parseInt($(S.map._container).css('width')) / 4 
                      var table = ['<table id=mydevs>']
                      $.each(Object.keys(S.devs), function(i,d) {
                        d = S.devs[d]
                        table.push('<tr id=device-'+d.mac+'>')
                        table.push('<td id=mac><div>' + '<a style="cursor: pointer" onclick=track("' + d.mac + '")>' + d.name + '</a>:' + d.vendor + '</div></td>')
                        //table.push('<td id=sensors><div>' + d.sensors.join(', ') + '</div></td>')
                        //table.push('<td id=lastseen><div>' + d.lastseen + '</div></td></tr>')
                      })
                      table.push('</table>')
                      if(typeof S.dialog != 'undefined') {
                        S.dialog.setSize([mx,my])
                        S.dialog.setLocation([45,45])
                        S.dialog.setContent(table.join(''))
                        return
                      } else {
                          S.dialog = L.control.dialog({size:[my,mx], minSize: [70,30],anchor:[20,20]})
                                              .setContent(table.join(''))
                                              .addTo(S.map)
                      }
          }
  })
  
  //$('div.leaflet-control-dialog').css('background','rgba(100,100,100,.1)')
}

function getLocatable() {
  $.ajax({ url: '/api/locatable',
           type: 'GET',
           success: function(l) {
             //console.log(l)
             if((typeof l != 'undefined')) {
               S.data.locatable = l.data
               //console.table(S.data.locatable)
               Object.keys(S.data.locatable).forEach(function(i) {
                  //console.log(S.data.locatable[mac][0]['loc'])
                  addLocated(S.data.locatable[i]['mac'], S.data.locatable[i]['location'], S.data.locatable[i]['rssi'], S.data.locatable[i]['locations'])
               })
             } else {
               return
             }
           }
         })
  drawDialog()
}

function rssiToMeters(rssi, multiplier, txpower) {
  if(typeof multiplier == 'undefined') multiplier = 1
  if(typeof txpower == 'undefined') txpower = -27
  var distance = Math.pow(10, ((rssi*multiplier) + 38.45) / txpower);
  return distance
}

function getTrack(mac) {
  $.ajax({ url: '/api/track/' + mac,
           type: 'GET',
           success: function(data) {
              drawTrack(data.data)
					 }
				})
}

function toggleTracking() {
  if(S.maps.tracking) {
		S.maps.tracking = 0
    delTimer('track')
		if(S.hasOwnProperty('dialog'))
			S.dialog.removeFrom(S.map)
  } else {
		getOwn()
    S.maps.tracking = 1
  }
}

function toggleLocating() {
  if(S.maps.locating) {
		S.maps.locating = 0
		delTimer('locate')
		if(S.hasOwnProperty('dialog'))
			S.dialog.removeFrom(S.map)
  } else {
		S.maps.locating = 1
		addTimer('locate','getLocatable()',15)
    getLocatable()
  }
}

//from stackexplorer/43167417
//var distance = getDistance([lat1, lng2], [lat2, lng2])

function getDistance(origin, destination) {
	function toRadian(degree) {
			return degree*Math.PI/180;
	}
    // return distance in meters
  var lon1 = toRadian(origin[1]),
      lat1 = toRadian(origin[0]),
      lon2 = toRadian(destination[1]),
      lat2 = toRadian(destination[0]);

  var deltaLat = lat2 - lat1;
  var deltaLon = lon2 - lon1;

  var a = Math.pow(Math.sin(deltaLat/2), 2) + Math.cos(lat1) * Math.cos(lat2) * Math.pow(Math.sin(deltaLon/2), 2);
  var c = 2 * Math.asin(Math.sqrt(a));
  var EARTH_RADIUS = 6371;
  
  return c * EARTH_RADIUS * 1000;
}


window.onready = setTimeout(drawMap,1000)
