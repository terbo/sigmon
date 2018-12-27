    // words have power, just like mirrors
    $(document).ready(function() {
      sigmonDemo = function() {
        var intro_time = 3600
        var subtitle_time = 2900
        var modular_time = 900
        var demo_time = 10000
        var intro_loop = 1
        var demo_loop = 0
       
        $('div#background').animate({opacity:0.6},2000)

        if ( $('.title').length ) {
          $('.title').animate({
              fontSize: '8em',
              opacity: 1.0,
              align: 'center',
              padding: '1.8em',
            }, intro_time, function() {
              $('.description').animate({
                opacity: 1.0,
                align: 'right',
              }, subtitle_time, function() {
                $('i#modular').html('modular ')
                              .animate({fontSize: '1.1em'},modular_time)
              })
          })
              
          $('.title').animate({opacity:0,fontSize: '.5em'},demo_time,showGraph)
        }
        
        if ( $('#toggler').length ) {
          $('#toggler').on('click',function(e) {
            $(this).animate({'opacity':'1.0'},800)
            $('a').toggle()
            if ( graph.cfg.bgcolor == 'black' ) {
              graph.cfg.bgcolor = 'white'
              $('body').css('background','white')
            } else {
              graph.cfg.bgcolor = 'black'
              $('body').css('background','black')
            }
          })
        }
      }
      
      showGraph = function() {
          $('.title').toggle()
          graph = new Graph()
          graph.show()
          graph.update()
          setTimeout('graph.autoRefresh()',2000)
          function watchInput() {
            $('input').on('click',function(e) {
              $('input').one('mouseleave',function(e) {
              id = $(this).attr('id')
              graph.cfg[id] = $(this).val()
              })
            })
          }
      }
      
      Graph = function() {
        this.graph_time = 5000
        this.datas = {}
        this.sensors = []
        this.macs = []
        this.ssids = []
        this.graph_id = 'graph' 
        this.graph_idx = '#graph' 

        this.cfg = {
            w: $(window).width() * .95,
            h: $(window).height() * .95,
            probeFetch: 10,
            // colors
            colMac: 'green',
            colRoot: 'beige',
            colSensor:'blue',
            colSsid:'red',
            // radius
            cMac: 4,
            cSsids: 6,
            cSensors: 7,
            cRoot: 9,
            cFudge: 8,
            // fudges
            iWeight: 0.0005,
            wPos: 90,
            wDiv: 1,
            wInc: 1,
            wSub: 0,
            wSensor: 2,
            wMacSsid: 1,
            wLink: 1,
            Links: 1,
            // packet loading
            randomlow: 4000,
            randomhigh: 8000,
            // physics
            charge: -50000,
            gravity: 1,
            friction: 0.02,
            maxnodes: 50,
            maxsensors: 5,
            cullTime: 90,
        }
       
        this.startDebug()          
        
        $(window).resize(function() {
          graph.cfg.w = $(window).width()
          graph.cfg.h = $(window).height()
        })
      }

      Graph.prototype.Set = function(k,v) {
        return this[k] = v
      }
      
      Graph.prototype.show = function() {
          console.log('Showing graph ...')
          this.w = this.cfg.w
          this.h = this.cfg.h
          
          this.color = d3.scale.category10() 
          
          graph_div = $('<div>')
          $(graph_div).attr('id',this.graph_id)
                      .prependTo('body')
          
          this.graph = d3.select(this.graph_idx)
                         .append('center')
                         .append('svg')
                         .attr('width',this.w)
                         .attr('height',this.h)
                         .attr('pointer-events','all')
                         .attr('viewBox','0 0 '+this.w+' '+this.h)
                         .attr('preserveAspectRatio','xMinYMin')
                         .append('svg:g')
          
          $(this.graph_idx).animate({opacity:1.0},this.graph_time)

          this.force = d3.layout.force()
          this.nodes = this.force.nodes()
          this.links = this.force.links()
          
          this.addNode('Sigmon','root')
          
          //fields = ['Devices','Software','Privacy']
          
          //for (var f in fields) {
          //  this.addNode(fields[f])
          //  this.addLink(fields[f],'Sigmon',10)
          //}
      }

      Graph.prototype.startDebug = function() {
        if ( ! $('#graphDebug').length ) {
          $('<div id="graphDebug"></div>').prependTo('#row2col2')
          $('<div id="graphData"></div>').prependTo('#row3col1')
        }
      }

      Graph.prototype.dbg = function(str) {
        return
        $('<div>'+str+'</div>').prependTo('#graphDebug')
        if ( this.nodes ) {
         dbdump = this.dumpGraph()
         $('<div>Nodes:<br>'+JSON.stringify(dbdump.nodes)+'</div>').prependTo('#graphData')
         $('<div>Totals:<br>'+JSON.stringify(dbdump.totals)+'</div>').prependTo('#graphData')
        }
        console.log(str)
      }

      Graph.prototype.dumpGraph = function() {
        var n = {}, l = {}, v
        for (var n_ in this.nodes) {
          node = this.nodes[n_]
          n[node.id] = [ node, this.countLinked(node.id), this.countLinks(node.id) ]
        }
        var t = this.nodes.length
        var tl = this.links.length
      
        return {totals:{nodes:t,links:tl},nodes:n}
      }
      
      Graph.prototype.linkSpacing = function(node) {
        return this.cfg.wLink //Math.round(node.value/100)
      }
      
      Graph.prototype.incWeight = function(id) {
        for ( var n in graph.nodes ) {
          node = graph.nodes[n]
          if ( node.id == id)
              //this.dbg(graph.nodes[0].weight+=(this.incWeight+this.incWeightRoot))
             return this.dbg(graph.nodes[n].weight)
        }
      }

      Graph.prototype.followsMouse = function(id) {
        node = this.findNode(id)
        d3.select(node)
      }

      Graph.prototype.addNode = function(id,type) {
          if ( this.nodes.length > this.cfg.maxnodes ) {
            return
          }
          if (nweight = this.incWeight(id)) {
            this.dbg('Incremented weight of '+id+' :'+nweight)
            return
          }
          
          this.nodes.push({id: id})
          
          if (type == 'root') {
            this.dbg('Adding root node!')
            this.root = id
            //this.followsMouse(id)
          } else if (type == 'sensor') {
            this.dbg(this.sensors + ') Adding sensor ['+id)
            this.sensors.push(id)
          } else if (type == 'ssid') {
            this.dbg(this.nodes.length + ') Adding SSID ['+id)
            this.ssids.push(id) 
            //this.flash(id)
          }
          else {
            this.dbg(this.nodes.length + ') Adding mac ['+id)
            this.macs.push(id)
            //this.blink(id)
          }
          //this.pulse(id,'root')
          this.update()
      }

      Graph.prototype.addLink = function(s,t,v) {
            this.dbg('Adding link from "'+s+'" to "'+t+'" with value of "'+v+'"')
            this.links.push({source: this.findNode(s), target: this.findNode(t), value: v})
      }

      Graph.prototype.findNode = function(id) {
            for (var i in this.nodes) { if (this.nodes[i]['id'] === id) return this.nodes[i] }
      }

      Graph.prototype.update = function() {
            var link = this.graph.selectAll('line').data(this.links, function(d) {
                  return d.source.id + '-' + d.target.id })

            link.enter().append('line')
              .attr('id', function(d) { return d.source.id + '-' + d.target.id })
              .attr('stroke-width', function(d) { return d.value })
              .attr('class','link')
            link.append('title') .text(function (d) { return d.id })
            link.exit().remove()
            var node = this.graph.selectAll('g.node').data(this.nodes, function (d) { return d.id })

            var nodeEnter = node.enter().append('g')
              .attr('class', 'node') .call(this.force.drag)

            nodeEnter.append('svg:circle')
              .attr('r', function(d) {
                if ( $.inArray(d.id,graph.macs) > 0) {
                  cnt =  graph.countLinked(d.id) + graph.cfg.cMac
                } else if ($.inArray(d.id,graph.ssids) > 0) {
                  cnt =  graph.countLinked(d.id) + graph.cfg.cSsid
                } else if($.inArray(d.id,graph.sensors) > 0 ) {
                  cnt =  graph.countLinked(d.id) + graph.cfg.cSensor
                } else {
                  cnt =  graph.cfg.cRoot
                }
                graph.dbg('Returning node radius for "'+d.id+'": '+cnt)
                return cnt
              })
              .attr('id', function (d) { return 'Node;' + d.id })
              .attr('class', 'nodeStrokeClass')
              .attr('fill', function(node) {
                        graph.dbg('Choosing color for '+node.id)
                        if ($.inArray(node.id,graph.macs) > 0) {
                          clr = graph.cfg.colMac
                        } else if ($.inArray(node.id,graph.ssids) > 0) {
                          clr = graph.cfg.colSsid
                        } else if ($.inArray(node.id,graph.sensors) > 0) {
                          clr = graph.cfg.colSensor
                        } else {
                          clr = graph.cfg.colRoot
                        }
                        graph.dbg('Chosen: '+clr)
                        return d3.rgb(clr)
                      })
            nodeEnter.append('svg:text')
              .attr('class', 'textClass').text(function(d) { return d.id })
            var node = this.graph.selectAll('g.node')
              .data(this.nodes, function (d) { return d.id })

            var nodeEnter = node.enter().append('g')
              .attr('class', 'node') .call(this.force.drag) 
            nodeEnter.append('svg:circle')
              .attr('r', function(d) { return graph.countLinks(d.id) + graph.cfg.wLinks })
              .attr('id', function (d) { return 'Node;' + d.id })
              .attr('class', 'nodeStrokeClass')
              .attr('fill', function(d) { return graph.findColor(d) })

            nodeEnter.append('svg:text')
              .attr('class', 'textClass')
              .attr('x', function(node) { return graph.countLinks(node.id) * 2 })
              .attr('y', '.11em')
              .attr('fill', function(d) {
                        graph.dbg('Choosing color 2 (txt?)for '+node.id)
                        if ($.inArray(node.id,graph.macs) > 0) {
                          clr = graph.cfg.colMac
                        } else if ($.inArray(node.id,graph.ssids) > 0) {
                          clr = graph.cfg.colSsid
                        } else if ($.inArray(node.id,graph.sensors) > 0) {
                          clr = graph.cfg.colSensor
                        } else {
                          clr = graph.cfg.colRoot
                        }
                        graph.dbg('Chosen: '+clr)
                        return d3.rgb(clr)
                      })
              .text(function (d) { return d.id })

            node.exit().remove()

            this.force.on('tick', function () {
              node.attr('transform', function (d) { return 'translate(' + d.x + ',' + d.y + ')' })

                link.attr('x1', function (d) { return d.source.x })

                .attr('y1', function (d) { return d.source.y })
                .attr('x2', function (d) { return d.target.x })
                .attr('y2', function (d) { return d.target.y })
              })

            this.force.gravity(this.cfg.gravity)
                      .charge(this.cfg.charge)
                      .friction(this.cfg.friction)
                      .linkDistance( function(d) {
                          return graph.linkSpacing(d)} ) //* 5
                      .size([this.cfg.w, this.cfg.h])
                      .start()
            
      
      }
        
      Graph.prototype.countLinks = function(node) {
        c = 0
        for(var i in graph.links) {
          if(graph.links.hasOwnProperty(i)) {
            if(typeof(graph.links[i].target) != 'undefined') {
              if(graph.links[i].target.id == node) {
              c += 1
              }
            }
          }
        }
        return c
      }
      
      Graph.prototype.countLinked = function(node) {
        c = 0
        for(var i in graph.links) {
          if(graph.links.hasOwnProperty(i)) {
            if(typeof(graph.links[i].source) != 'undefined') {
              if(graph.links[i].source.id == node) {
                c += 1
                }
              }
            }
          }
          return c
      }

      Graph.prototype.weightRssi = function(rssi) {
          wrssi = rssi + this.cfg.wPos
          wrssi /= this.cfg.wDiv
          wrssi -= this.cfg.wSub
          wrssi = Math.round(wrssi)
          this.dbg('Input RSSI: '+rssi+' - Weight: ' +wrssi)
          return wrssi
      }

      Graph.prototype.randInterval = function() {
        return Math.round(Math.random() *
                          (this.cfg.randomlow -
                          this.cfg.randomhigh) +
                          this.cfg.randomlow +
                          this.cfg.randomhigh)
      }
      
      Graph.prototype.autoRefresh = function() {
        setTimeout('graph.autoRefresh()', this.randInterval())
        $.ajax({type:'GET',
                url: '/api/tail/'+this.cfg.probeFetch,
                success: function(data) {
                  graph.datas = data.data
                }
        })
        
        for (var D in this.datas) {
          D = this.datas[D]
          // pulses along the links?
          mac = D.mac.replace(/:/g,'').substr(1,4)
          
          if ($.inArray(mac,this.macs) === -1) { // new mac
            this.addNode(mac,'mac')
          } //if(node = this.findNode(D.mac)) { // updating mac?
            //node.weight+=this.cfg.wInc
          if ($.inArray(D.sensor,this.sensors) === -1) { // new sensor
              this.addNode(D.sensor,'sensor')
              this.addLink('Sigmon',D.sensor,this.cfg.wSensor)
            this.addLink(D.sensor,mac,this.weightRssi(D.rssi))
          }
          
          if ($.inArray(D.ssid,this.ssids) === -1) { // new ssid
            this.addNode(D.ssid,'ssid')
            this.addLink(mac,D.ssid,this.cfg.wMacSsid)
          } else {
            this.dbg('Got unknown packet? '+JSON.stringify(D))
          }
        }

        this.update()
    }
})

// vim: set ts=2 sw=2 ai expandtab softtabstop=2
