// starting over a gain ..
// d3g v 0.01 (from d3graph.js)
//

// needs a packet line graph
// sensor infos
// counters
// interface for interacting with infos?????

D3G.prototype.addNode = function(id,type) {
	if(! d3g.findNode(id)) {
		d3g.log('Adding node ' + id + ' type ' + type)
    try {
      d3g.nodes.push({id:id,type:type})
    } catch (e) {
      d3g.log('ERROR - ' + e)
      return
    }
    if(type == 'mac')
      d3g.counter.macs ++
    else if(type == 'ssid')
      d3g.counter.ssids ++
    else if(type =='ap')
      d3g.counter.aps ++
  } else {
		d3g.log(id + ' has already been seen ...')
	}
}

D3G.prototype.cullNodes = function() {
  d3g.nodes.forEach(function(n) {
    if((n.type == 'mac') || (n.type == 'ssid')  || (n.type == 'ap')) {
      if ( n.hasOwnProperty('lastseen') && parseInt((new Date() - n.lastseen) / 1000) >= d3g.cullTime ) {
        d3g.log(n.id + ' expires')
        try {
          d3g.delNode(n)
        } catch (e) {
          d3g.log('ERROR - ' + e)
          console.table(d3g.nodes)
          console.table(d3g.links)
        }
      }
    }
  })

  return this
}
  
D3G.prototype.addLink = function(id,target,weight) {
  if((typeof id == 'undefined') || (typeof target == 'undefined') || (id.length == 0) || (target.length == 0)) {
      d3g.log('ERROR - Sent [' + id + ',' + target + ',' + weight + ']')
      return
	} else if ((typeof weight == 'undefined') || (weight.length <= 0) || (typeof weight != 'number')) {
      d3g.log('WEIGHT ERROR - Sent [' + weight + ']')
    return
  }

	if(d3g.isLinked(id,target)) {
		if(d3g.findNode(id).type != 'ap')
      d3g.log('ERROR - ' + id + ' is already linked to ' + target)
		return
	}

  d3g.log('Adding Link for ' + id + ' to ' + target + ' with weight of ' + weight)

  try {
    if(d3g.findNode(id))
      d3g.links.push({source: d3g.findNode(id),
                     target: d3g.findNode(target), value: weight})
  } catch (e) {
    d3g.log('ERROR - Adding ' + id + ': ' + e)
    return this
  }

  d3g.update()
  
  return this
}

D3G.prototype.findNode = function(id) {
  if(typeof id != 'string')
    id = id.id
   
  for (var i in d3g.nodes)
    if (d3g.nodes[i]['id'] == id || d3g.nodes[i]['id'] == id.id)
      return d3g.nodes[i]
  
  return false
}

D3G.prototype.log = function(l) {
  if(d3g.debug)
    console.log(l)
  return this
}

D3G.prototype.delNode = function(n) {
  if (typeof n == 'string')
    node = d3g.findNode(n)
  else if(typeof n == 'object')
    node = d3g.findNode(n.id)
  else { return d3g.log('ERROR: - ' + n + ' is not a valid node') }
  
  if(!node)
    return d3g.log('No node: ' + id)

  d3g.log('Splicing ' + node.id + ' (' + node.index + ')' )
  //d3g.log(d3g.links.length + ' links and ' + d3g.nodes.length + ' nodes before,')
  d3g.nodes.splice(node.index,1)
  d3g.links = d3g.links.filter(function(l) {
    return ((l.source != node) && (l.target != node))
  })

  //d3g.log('Node Result: ' + d3g.findNode(n) + ' <--')
  //d3g.log(d3g.findLinks())
  //d3g.log(d3g.links.length + ' links and ' + d3g.nodes.length + ' nodes after.')
}

D3G.prototype.findLinks = function(node) {
  var n = d3g.findNode(node)
  if(!n) {
    d3g.log('WTF - no node!')
    return
  }

  var out = []
  d3g.links.forEach(function(l) {
    if( d3g.isLinked(n, l.source) )  {
      out.push([l.source, 'source'])
    } else if( d3g.isLinked(n, l.target) )  {
      out.push([l.target, 'target'])
    }
  })
  return out
}

D3G.prototype.drawGraph = function() {
  d3g.log('Drawing graph')
	
	d3g.force = d3.layout.force()
  d3g.nodes = d3g.force.nodes()

  d3g.svg = d3.select(d3g.div)
      .append('svg')
      .attr('width',d3g.w)
      .attr('height',d3g.h)
      .attr('top','0')
      .attr('left','0')
      .attr('opacity','0.9')
      .attr('pointer-events','all')
      .attr('viewBox','0 0 '+d3g.w+' '+d3g.h)
      .attr('preserveAspectRatio','xMinYMin')
      .append('g')

  d3g.links = d3g.force.links()
	
	d3g.drawn = true
  
  return this
}

D3G.prototype.getAjax = function() {
	$.ajax({type:'GET',
          url: d3g.ajaxURL,
          success: function(data) {
            d3g.counter.probes += data.data.probes.length
            d3g.data = data.data
						d3g.process()
						d3g.update()
            d3g.cullNodes()
					}
  })
  return this
}

D3G.prototype.process = function() {
	d3g.data.aps.forEach(function(p) {
    mac = p._id.replace(/:/g,'') //.substr(0,5)
    
    if(d3g.findNode(mac) && d3g.aps.hasOwnProperty(mac)) {
      d3g.aps[mac].minrssi = p.minrssi
      d3g.aps[mac].maxrssi = p.maxrssi
      d3g.aps[mac].lastrssi = p.lastrssi
      d3g.aps[mac].sensors = p.sensors
      d3g.aps[mac].beacons ++
    } else {
      d3g.aps[mac] = {
        beacons: 1,
        packets: 1,
        minrssi: p.minrssi,
        maxrssi: p.maxrssi,
        lastrssi: p.lastrssi,
        ssids:  p.ssids,
        sensors: p.sensors,
        vendor: p.vendor,
      }

      d3g.addNode(mac,'ap')

      p.sensors.forEach(function(sensor) {
        d3g.addLink(mac, sensor, (p.lastrssi + 100) * p.sensors.length)
      })
    }
    d3g.findNode(mac).lastseen = new Date()
  })

  d3g.data.datapkts.forEach(function(p) {
    if(d3g.aps.hasOwnProperty(p.dst_mac)) {
      d3g.aps[p.dst_mac].packets ++
    }
    if(d3g.aps.hasOwnProperty(p.src)) {
      d3g.aps[p.src].packets ++
    }
  })

  d3g.data.probes.forEach(function(p) {
		if (d3g.onlyOwned && (! S.owndevs.hasOwnProperty(p.mac)))
        return
    
    mac = p.mac.replace(/[_:]/g,'') //.substr(0,5)
    if(d3g.findNode(mac) && d3g.macs.hasOwnProperty(mac)) { // already seen
      d3g.macs[mac].probes = p.probes
			d3g.macs[mac].minrssi = p.minrssi
		  d3g.macs[mac].maxrssi = p.maxrssi
		} else {
      d3g.macs[mac] = {
				probes: p.probes,
				sensors: p.sensors,
				ssids: p.ssids + p.allssids,
				vendor: p.vendor,
				tags: p.tags,
				firstseen: p.firstseens,
				lastseen: p.lastseens,
				minrssi: p.minrssi,
				maxrssi: p.maxrssi,
				sessions: p.sessioncount,
        }
			
      d3g.addNode(mac,'mac')

      p.sensors.forEach(function(sensor) {
        if(!d3g.isLinked(mac,sensor))
          d3g.addLink(mac,sensor,p.probes) // islinkEd
      })
      
      p.ssids.forEach(function(ssid) {
        if (ssid.length == 0)
            ssid = '[hidden]'
        
        if(! d3g.ssids.hasOwnProperty(ssid) ) {
          d3g.ssids[ssid] = 1
          if(!d3g.findNode(ssid)) {
            d3g.addNode(ssid,'ssid')
          }
          if(!d3g.isLinked(mac,ssid))
            d3g.addLink(mac,ssid,p.probes)
        }
       
        d3g.findNode(ssid).lastseen = new Date()
      })
    }
    d3g.findNode(mac).lastseen = new Date()
	})
  return this
}

D3G.prototype.isLinked = function(s,t) {
  for(var i in d3g.links)
    if(d3g.links.hasOwnProperty(i))
      if(typeof(d3g.links[i].source != 'undefined'))
        if(d3g.links[i].source.id == s)
          if(typeof(d3g.links[i].target) != 'undefined')
            if(d3g.links[i].target.id == t)
              return d3g.links[i].value
  return false
}

D3G.prototype.getStroke = function(c) {
  if(c.type == 'sensor')
    return d3.rgb('white')
  if(c.type == 'mac')
    return d3.rgb('blue')
  if(c.type == 'ssid')
    return d3.rgb('orange')
  if(c.type == 'ap')
    return d3.rgb('grey')
  return this
}

D3G.prototype.getRadius = function(c) {
  if(c.type == 'sensor')
    return(15 + d3g.links.filter(function(l) { return l.target.id == c.id }).length)
  if(c.type == 'mac')
    return(10 + d3g.links.filter(function(l) { return l.source.id == c.id }).length)
  if(c.type == 'ssid')
    return(9 + d3g.links.filter(function(l) { return l.target.id == c.id }).length)
  if(c.type == 'ap')
    return(4 * d3g.aps[c.id].beacons)
  return this
}

D3G.prototype.getFill = function(c) {
  if(c.type == 'sensor')
    return d3.rgb('green')
  if(c.type == 'mac')
    return d3.rgb('blue')
  if(c.type == 'ssid')
    return d3.rgb('red')
  if(c.type == 'ap')
    return d3.rgb('lightorange')
  return this
}

D3G.prototype.showName = function(node) {
  if (node.type == 'sensor' || node.type == 'ssid')
    return node.id
  if(node.type == 'mac')
    return node.id.substring(0,5) + ' ' + d3g.macs[node.id].vendor
  if(node.type == 'ap')
    return d3g.aps[node.id].ssids[0]
  return this
}

D3G.prototype.update = function() {
  $($('.counter#aps')[0]).html(d3g.counter.aps)
  $($('.counter#macs')[0]).html(d3g.counter.macs)
  $($('.counter#ssids')[0]).html(d3g.counter.ssids)
  $($('.counter#probes')[0]).html(d3g.counter.probes)
  $($('.shown')[0]).html(d3g.nodes.length)

  var node = d3g.svg.selectAll('g.node')
                     .data(this.nodes, function (d) { return d.id })

  var nodeEnter = node.enter().append('g')
        .attr('class', 'node')
        .call(this.force.drag)

  nodeEnter.append('circle')
    .attr('r', d3g.getRadius)
    .attr('id', function (d) { return 'Node;' + d.id })
    .attr('class', 'nodeStrokeClass')
    .attr('stroke-width','1px')
    .attr('stroke',d3g.getStroke)
    .attr('opacity','0.9')
    .attr('fill', d3g.getFill)
    /*.attr("cx", function(d) { n=d3g.findNode(d.id)
                  l = d3g.findLinks(n.id)
                  console.log('L>>' + l)
                  if(l.length)
                    return d.px = (l.target.px + l.target.py) * 0.5
                  else
                    return d.px = 500 })
    .attr("cy", function(d) { n=d3g.findNode(d.id);
                  l = d3g.findLinks(n.id)
                  console.log('L>>' + l)
                  if(l.length)
                    return d.py = (l.target.px + l.target.py) * 0.5
                  else
                    return d.py = 500 })
 */ 
  node.exit().remove()

  nodeEnter.append('text')
    .attr('x', d3g.displayNameX)
    .attr('y', d3g.displayNameY)
    .attr('stroke-width',d3g.strokeWidth)
    .attr('stroke',d3g.strokeColor)
    .attr('font-weight',d3g.fontWeight)
    .attr('font-family',d3g.fontFamily)
    .attr('font-size',d3g.fontSize)
    .attr('fill',d3g.fillColor)
    .style('opacity', '0.9')
    .text(d3g.showName)
  

  d3g.force.on('tick', function() {
              if ( d3g.autoPhysics ) {
                var k = Math.sqrt(d3g.nodes.length / (d3g.w * d3g.h));
                d3g.charge = -10 / k;
                d3g.gravity = 100 * k;
              }

              node.attr('transform', function (d) {
                return 'translate(' + d.x + ',' + d.y + ')'
              })
  })
 
  try {

  d3g.force
      .gravity(d3g.gravity)
      .charge(function (d, i) { return i ? d3g.charge / 2 : d3g.charge})
      .friction(d3g.friction)
      .linkDistance(d3g.linkDistance)
      .size([d3g.w, d3g.h])
      .start()
  } catch (e) {
    d3g.log('ERROR - force - ' + e)
    console.table(d3g.nodes)
    console.table(d3g.links)
    return d3g.stop()
  }
  
  return this
}

D3G.prototype.stop = function() {
	d3g.log('Stopping d3g')
  clearInterval(d3g.timer)

  return this
}

D3G.prototype.run = function() {
  if((typeof S == 'undefined') 
    || (!S.hasOwnProperty('sensors'))
    || (S.sensors.length <= 0)) {
  
	setTimeout('d3g.run()',1000)
	return
	}

  if(!d3g.drawn) {
		d3g.drawGraph()

		//console.log(S.sensors)
    for(s in S.sensors) {
			d3g.log('Adding sensor ' + s)
      d3g.addNode(s, 'sensor')
      
      var n = d3g.findNode(s)
			var facing = S.sensors[s].longlat.orientation
			
      n.fixed = 1
      
      d3g.log(s + ' is facing ' + facing)
      
      if(facing == 'NE') {
            n.px = d3g.w - 110
            n.py = 110
      } else if(facing == 'NW') {
            n.px = 110
            n.py = 110
      } else if(facing == 'SE') {
            n.px = d3g.w - 110
            n.py = d3g.h - 110
      } else if(facing == 'SW') {
            n.px = 110
            n.py = d3g.h - 110
      }
		}
	
	}
	
	if(typeof d3g.timer == 'undefined')
		d3g.timer = setInterval('d3g.getAjax()',d3g.refreshInterval)

  d3g.getAjax()

  return this
}

function D3G(div, opts) {
  this.version = '0.01'
  this.debug = 0
  this.div = div || '#d3g'
  this.drawn = 0
  
	this.onlyOwned = false
  
  this.ajaxURL = '/api/overview/1'
  this.sensorURL = '/api/sensors/full'
  
	this.w = $(window).width()
  this.h = $(window).height()
	
  this.cullTime = 45
  this.counter = {'macs':0,'ssids':0,'aps':0, 'probes': 0}

	this.aps = {}
  this.macs = {}
	this.ssids = []
	this.data = []
	this.sensors = []
	
  this.timer = undefined
  this.refreshInterval = 45 * 1000
	
  this.fontFamily = 'Verdana'
	this.fontSize = '1em'
	this.fontWeight = 'italic'
	this.strokeWidth = '.3px'
  this.strokeColor = d3.rgb('red')
  this.fillColor = d3.rgb('red')
  this.displayNameX = '.8em'
	this.displayNameY = '-.30em'

	this.autoPhysics = false
	this.charge = -100000
	this.gravity = .999
	this.friction = 0.03
  this.linkDistance = 40

  console.log('d3g version ' + this.version + ' loaded')
  
  return this
}

var d3g = new D3G('#d3g')
window.onload = function() { getSensors(); getOwn(); d3g.run() }

// vim: tabstop=2 shiftwidth=2 expandtab ai
