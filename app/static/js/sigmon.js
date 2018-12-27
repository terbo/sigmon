// perhaps more than control of personal identity and knowledge of life, its origin, and purpose
// we are controlled by an incorrect understanding of time

// i stand before his majestry
// asking for his pittance
// while knowing that his powers only possible with pennies
// already stolen one
// and once i get a third
// i'll look them over quickly
// then i'll toss them too the curb
// death penalty evaded now hes asking for his payment
// i'll tell him that on tuesday, i probably will have made it
// ghost
// and whiter than a sheet in the clouds
// finally thinking to my self, then i say it out loud
// that man probably could have killed me
// 

// only vibratory resonance
// in incremental measurements
// sever us, 

// most misunderstood in this realm are
// identity and divinity
// beings with no real idea of what they are
// or awareness their influence is on their environment
// disabled from their own chosen purpose
// serving the purpose of other entities
// 
// these are things that cannot be shown
// and in expecting them to be taught
// a primary misunderstanding is cultivated
// what is impossible is to lead one to themselves
//
// what is unknowable is that which does not fit
// into the mind, is not of the mind, and is not of time
// 

// leaflet panel
// leaflet haetmap
// leaflet drawing ##
// leaflet indoors
// time series
// history
// quadtree

window.onload = sigmonInit

window.S = {'startdate': 0,
         'enddate': 0,
         'minutes': 15,
         'debug': 1,
         'data': {},
				 'located': {},
         'locmarks': {},
         'words': [],
         'poly': [],
         'gridsterEditable': 0,
         'weights': {'sigmon': 12,
                     'sensor': 11,
                     'ap': 10,
                     'device': 4,
                       },
         'keys': [],
         'timers': {},
         'notices': [],
         'charts': {},
         'sensors': [],
         'aps': [],
         'macs': [],
         'vendors': [],
         'ssids': {},
         'filters': {},
         'tags': [],
         'stats': [],
         'tracking': [],
         'log': function(st) {
            if ( S.debug ) {
              console.log(st)
            }
         },
         'evsearch': {  days: 4,
                        minthresh: 150,
                        maxthresh: 5000
                     },
}


String.prototype.hashCode = function() {
    var hash = 0, i, chr;
    if (this.length === 0) return hash;
    for (i = 0; i < this.length; i++) {
          chr   = this.charCodeAt(i);
          hash  = ((hash << 5) - hash) + chr;
          hash |= 0; // Convert to 32bit integer
        }
    return hash;
};


  // try and draw a circle from the points given as sensors?
  // or focus to the center of all drawn objects

  // how about have it request sensors location over REST


function tailProbes() {
  $.ajax({ url:'/api/tail',
           type: 'GET',
           success: function(data) {
                      S.data.tail = data.data
                      $('.currentmacs').html(data['current']['macs'])
                      $('.currentsensors').html(data['current']['sensors'])
                      $('.currentvendors').html(data['current']['vendors'])
                      $('.currentprobes').html(data['current']['probes'])
                      $('.currentssids').html(data['current']['ssids'])
                    }
         })
}

function updateSensor(obj, t) {
  var cmd;
  if(typeof t === 'undefined')
    cmd = 'edit'
  else
    cmd = 'locate'
  
  $.ajax({ url:'/api/sensors/'+cmd,
           type: 'POST',
           data: obj,
         })
  return true
}

function getOwn(mac, name) {
  query = '/api/owndevs'

  if(typeof mac != 'undefined') {
    method = 'POST'
    query += '/' + mac
    if(typeof name != 'undefined')
      query += '/' + name
  } else {
    method = 'GET'
  }

  $.ajax({ url: query,
           type: method,
           success: function(data) {
              S.owndevs = data.data
              },
           error: function(e) { console.log(e) }
         })
}

function getSensors() {
  $.ajax({ url:'/api/sensors/full',
           type: 'GET',
           success: function(data) {
              S.sensors = data.data
              },
           error: function(e) { console.log(e) }
         })
}

function drawSensors() {
  //console.log('Drawing sensors.')
  
  //if(typeof S !== 'undefined')
  //  if(S.hasOwnProperty('sensors') && (typeof S.sensors == 'undefined'))
  //    return //S.log('No sensors')
  //if ( ! $('div#sensorview').length )
  //  return //S.log('no div')

  $.each(S.sensors, function(i,obj) {
    var newsensor = $('div#sensorview').clone().toggle()
    $(newsensor).attr('id',i).addClass('sensor').toggle()
    //S.log('Drawing '+$(newsensor).attr('id'))

    var sensor = obj
    var stat = sensor.status
    var nfo = sensor.info
    var pps = sensor.stats || {minrssi:0,avgrssi:0,maxrssi:0}

    $(newsensor).find('.sensorinfoname').html(i)
    $(newsensor).find('.sensorinfodesc').html(nfo['desc'])
    $(newsensor).find('.sensorinfoserial').html(nfo['serial'])
    $(newsensor).find('.sensororientation').html(sensor['longlat']['orientation'])
    
    $(newsensor).find('.sensorrssi').html(Math.floor(pps.minrssi) + ', ' + Math.floor(pps.avgrssi) + ', ' + Math.floor(pps.maxrssi))
    $(newsensor).find('.sensorprobes').html(pps.probes)
    
    $(newsensor).find('.sensorinfossh').html(nfo['ip']+':'+sensor['ssh']['port'])
    $(newsensor).find('.sensorinforole').html(sensor['role'])
    $(newsensor).find('.sensorname').val(i)
    $(newsensor).find('.sensorlastseen').html(stat['lastseen'])
   
    var statusicon = $('<i>').addClass('fa')
    if ( stat['connected'] === true )
      statusicon
        .addClass('fa-check-circle')
        .css('color','green')
    else
      statusicon
        .addClass('fa-circle-o')
        .css('color','red')
      
    $(newsensor).find('.sensorconnected').append(statusicon)
    $(newsensor).find('.sensoraddress').val(nfo['ip'])
    $(newsensor).find('.sensorport').val(sensor['ssh']['port'])
    $(newsensor).find('.sensordesc').val(nfo['desc'])
    $(newsensor).find('.sensornotes').val(nfo['notes'])
    $(newsensor).find('.sensoros').val(nfo['os'])
    $(newsensor).find('.sensorbrand').val(nfo['brand'])
    $(newsensor).find('.sensormodel').val(nfo['model'])
    $(newsensor).find('.sensorserial').val(nfo['serial'])
    $(newsensor).find('.sensorlocation').val(sensor['longlat'].coordinates[0] + ',' + sensor['longlat'].coordinates[1])
    $(newsensor).find('.sensorinterfaces').val(JSON.stringify(sensor['iface']))
    $(newsensor).find('.sensorssh').val(JSON.stringify(sensor['ssh']))
    $(newsensor).find('#sensorcancelsubmit').
      click( function(e) {
        e.preventDefault();
        $(newsensor).find('form').toggle()
        $(newsensor).find('.sensorinfo').toggle()
      })
    $(newsensor).find('#sensorsubmit').
      click( function(e) {
        e.preventDefault();
        var form = $(newsensor).find('form').serialize()
        if(updateSensor(form)) {
          $(newsensor).find('form').toggle()
          $(newsensor).find('.sensorinfo').toggle()
        } else { S.log('Error ::: ' + form) }
      })
    $(newsensor).find('#sensoredit').
      click(function() {
       $(newsensor).find('.sensoreditor').toggle()
       $(newsensor).find('.sensorinfo').toggle()
      })
    
    $(newsensor).appendTo('#sensors')
  })
  
  
  /*var sensors = $('.sensor')
  $('.sensor').remove()
  var row = 0, i = 0

  $.each(sensors,function(s) {
    console.log($(sensors[i]).attr('id'), ' moved/drawn')
    if (i % 3 === 0)
      row++
    //S.gridster.add_widget(sensors[i],row, i++)
  })
  return S.gridster
  */

 $('div').css('display','inline')
 $('#sensorview').css('display','none')
}

function timeSelector() {
return true
/*  if ( ! $('#timeselectin').length )
    return
  
  var current = 15
  S.startdate = new Date() - (current * 1000)
  S.enddate = new Date()
  S.minutes = current
  var tm

  if ( current <= 60 ) { tm = ' minutes' }
  else if ( current < 1440 ) {
    tm = ' hours';
    current /= 60;
  } else { tm = ' days'; current /= 60; current /= 24;  }
  
  $('#timeselectin button').text(current+tm)
  $('#timeselectin li').click(function(e) {
    e.preventDefault();
    var URL = document.URL;
    var nt = $(this).attr('id');

    // this should be saved in a session, and ...?
    if(URL.indexOf('mins=') != -1) {
           URL = URL.replace(/mins=\d+/,'mins='+nt);
    } else {
          URL = URL + '?mins='+nt;
    }
    window.location = URL;
  })
*/  
}

function popinfo(t) {
  var id = $(this).attr('id')
  return 'All SSIDs: for '+id
}
function drawChart() {
  if ( ! $('div.graphics').length )
    return
  
  var count = new Array('count')
  var usage = new Array()
  var hour = new Array()

  var vendors = []
  
  if ( $('#vendorchart') )
    S.charts.vendor = c3.generate({
      bindto: '#vendorchart',
      data: {
        url: '/api/graph/vendors/1/24',
          mimeType: 'json',
          type: 'donut'
      },
      donut: {
        title: 'Vendors',
        label: {
          format: function(val,ratio,id) {
            return id.split(' ')[0]
          }
        },
      },
      onrendered: function() {
        setTimeout(function() {
          for (var x in S.charts.vendor.data()) {
            v = S.charts.vendor.data()[x]
            if (v.id.startsWith('Unknown') || v.id.startsWith('Google'))
              S.charts.vendor.hide(v.id)
            }
         }
        ,2500) }
    })
  
  if ( $('#dailygraph').length )
    S.charts.probe = c3.generate({
      bindto: '#dailygraph',
      data: {
          x: 'day',
          xFormat: '%d/%m/%Y %H:%M:%S',
          url: '/api/graph/daily/7/24',
          mimeType: 'json',
      },
      color: {
        probes: ['blue'],
        sessions: ['red'],
        new_devices: ['orange']
      },
      axis: {
        x: {
           type: 'timeseries',
           tick: { format: '%H:%M' }
        },
        sessions: {
          label: {
            format: function(val,ratio,id) {
              return id / 100
            }
          },
        }
      }
    });
 
  if ( $('#hourlygraph').length )
    S.charts.usage = c3.generate({
      bindto: '#hourlygraph',
      data: {
          x: 'hour',
          xFormat: '%d/%m/%Y %H:%M:%S',
          url: '/api/graph/hourly/7/24',
          mimeType: 'json',
      },
      color: {
        probes: ['green'],
        sessions: ['orange'],
        new_devices: ['purple']
      },
      axis: {
        x: {
         type: 'timeseries',
         tick: { format: '%m-%d %H:%M' }
        }
      }
    });

  if ( $('#heatmap').length) {
    $.ajax({type: 'GET',
            url: '/api/heatmap',
            success: function(d) {
              S.data.heatmap = d.data
              S.charts.heatmap = calendarHeatmap()
                        .data(S.data.heatmap)
                        .selector('#heatmap')
                        .tooltipEnabled(true)
                        .tooltipUnit('probe')
              S.charts.heatmap()
    }})
  }
}

function drawDataTables() {
  if ( $('#datatable').length ) {
          /*ajax: {
                  url: '/api/overview/15',
                  dataSrc:
                    function(d) { s.overview = d.data; return s.overview.probes }
                },*/
    S.datatable = $('#datatable').DataTable({
          autoWidth: true,
          paging: true,
          stateSave: true,
          colReorder: true,
          select: false,
          buttons  : ['colvis','copy','csv','pdf','print'],
          pagingType: 'numbers',
          responsive: {
              details: {
                  type: 'column',
                  target: '.details-control'
              }
          },
          columns  : [ { 'className': 'details-control',
                         'orderable': false,
                         'data': null,
                         'defaultContent': ''},
                       {'data':'sensors'},
                       {'data':'mac'},
                       {'data':'lastrssi'},
                       {'data':'probes'},
                       {'data':'ssids'},
                       {'data':'lastseen'},
                       {'data':'firstseen'},
                       {'data':'sessioncount'},
                       {'data':'tags',
                          'orderable': false },
                     ],
          })
    
    var n = $('#datatable_info')

    //$(l).prependTo(n)
    $(n).remove().prependTo(w)
    //$(f).remove().prependTo(w)
    
    
    var w = $('#datatable_wrapper')
    //$(w).find('.col-sm-6').removeClass('col-sm-6')
    //var f = $('#datatable_filter').remove()*/
    //$(f).appendTo(l) */

    var b = S.datatable.buttons().container()
    var l = $('#datatable_length')
    $(b).appendTo(l)
   
    $('#datatable_paginate').parent().prev('div').remove()
    $('#datatable_paginate').css('text-align','right')

    S.datatable.on( 'responsive-resize', function ( e, datatable, columns ) {
      var count = columns.reduce( function (a,b) {
        return b === false ? a+1 : a;
      }, 0 ); 
    })
  }

  if ( $('#btview').length ) {
      S.btview = $('#btview').DataTable({
          colReorder: true,
          paging: true,
          select: false,
          buttons  : ['colvis','copy','csv',,'pdf','print'],
          saveState: true,
          responsive: {
              details: {
                  type: 'column',
                  target: 'tr'
              }
          }
    })
    
    var b = S.btview.buttons().container()
    var l = $('#btview_length')
    $(b).appendTo(l)
    
    S.btview.on( 'responsive-resize', function ( e, datatable, columns ) {
      var count = columns.reduce( function (a,b) {
        return b === false ? a+1 : a;
      }, 0 ); 
    })
  }
  
  if ( $('#apview').length ) {
      S.apview = $('#apview').DataTable({
          colReorder: true,
          paging: true,
          select: false,
          buttons  : ['colvis','copy','csv','pdf','print'],
          saveState: true,
          responsive: {
              details: {
                  type: 'column',
                  target: 'tr'
              }
          }
    })
    var b = S.apview.buttons().container()
    var l = $('#apview_length')
    $(b).appendTo(l)
  
    S.apview.on( 'responsive-resize', function ( e, datatable, columns ) {
      var count = columns.reduce( function (a,b) {
        return b === false ? a+1 : a;
      }, 0 ); 
    })
  }
  
  if ( $('#dbtable').length ) {
      S.dbtable = $('#dbtable').DataTable({
          colReorder: true,
          paging: true,
          select: false,
          buttons  : ['colvis','copy','csv','pdf','print'],
          saveState: true,
          responsive: {
              details: {
                  type: 'column',
                  target: 'tr'
              }
          }
    })
    var b = S.apview.buttons().container()
    var l = $('#apview_length')
    $(b).appendTo(l)
  
    S.apview.on( 'responsive-resize', function ( e, datatable, columns ) {
      var count = columns.reduce( function (a,b) {
        return b === false ? a+1 : a;
      }, 0 ); 
    })
  }
}

function drawTags() {
  $('a.btn').addClass('btn-xs')
   
  $('a.btn:eq(0)').addClass('btn-primary')
  $('a.btn:eq(1)').addClass('btn-warning')
  $('a.btn:eq(2)').addClass('btn-info')
  $('a.btn:eq(3)').addClass('btn-info')
  $('a.btn:eq(4)').addClass('btn-info')
  $('a.btn:eq(5)').addClass('btn-danger')
   
  $('a.btn:eq(6)').addClass('btn-primary')
  $('a.btn:eq(7)').addClass('btn-warning')
  $('a.btn:eq(8)').addClass('btn-info')
  $('a.btn:eq(9)').addClass('btn-info')
  $('a.btn:eq(10)').addClass('btn-info')
  $('a.btn:eq(11)').addClass('btn-danger')
   
  $('a.btn:eq(12)').addClass('btn-primary')
  $('a.btn:eq(13)').addClass('btn-warning')
  $('a.btn:eq(14)').addClass('btn-info')
  $('a.btn:eq(15)').addClass('btn-info')
  $('a.btn:eq(16)').addClass('btn-info')
  $('a.btn:eq(17)').addClass('btn-danger')
  
  a = $('div.col-sm-6')[0]
  $('div.tags').parent().remove().appendTo(a)
  $('div.tags button').click(toggleTag)
}

function resized(){
    S.w = $(window).width()
    S.h = $(window).height()
    
    if(S.hasOwnProperty('map'))
      resizeMap()
    
    try {
      if($('#apview').length)

      if(S.w > 750)
        $('#apview').css('width','100%')

    /*  $('#apview').dataTable.resize();
    } catch (e) { console.log(e) }
    try {
      if($('#btview').length)
      $('#btview').dataTable.resize();
    } catch (e) { console.log(e) }
    try {
    if($('#datatable').length)
      $('#datatable').dataTable.resize();
    } catch (e) { console.log(e) }
    try {
    if($('#dbtable').length)
      $('#dbtable').dataTable.resize();
   */ } catch (e) { return false}

}

function toggleTag(e) {
  btn = e.target
  var alltags = [],
      filters = []
  
  $(btn).toggleClass('active')
  
  $('span.tags').each(function() {
    $(this).find('span').each(function(){
      var tag = $(this).attr('id');
      if( $.inArray(tag,alltags) === -1)  alltags.push(tag)
    })
  })
  
  $('div.tags button').each(function() {
    if ( $(this).hasClass('active') ) {
      filters.push($(this).attr('id'))
    }
  })
  
  S.datatable.search(filters.join(' ')).draw()
}

function eventDrops() {
  if ( ! $('#eventgraph').length )
    return
  
  var colors = d3.scale.category10();
  
  $.ajax({ url:'/api/eventgraph',
          type: 'GET',
            success: function(data) {
              data = data.data
              S.data.eventgraph = data
              
              range = eval(data.range)
              
              if (! range ) {
                S.log(data)
                S.log('no data')
                return
              }
              start = new Date(new Date() - (1000 * 60 * 60 * 24 * 4 * 6))
              console.log(start)
              end = new Date()
              
              data = eval(data.data) 
              
              S.charts.evchart = d3.chart.eventDrops()
              S.charts.evchart.start(start).end(end)
                      .eventLineColor(function(d, i) { return colors(i)})

              d3.select('#eventgraph')
                .datum(data)
                .call(S.charts.evchart)
          }
  })
}

function checkNotices() {
  $.ajax({ url:'/api/notices',
           type: 'GET',
        success: function(data) { 
            $.each(data.data, function(i,m) {
                addNotice(m)
            })
        }
  })
  
  //addTimer('notices','checkNotices()',180)
}

function addNotice(m) {
  // make S.notices.messages and just do 'in'?
  for(var n in S.notices) {
    if (m.message == S.notices[n].message) {
      return
    }
  }
  S.log('Adding notice: '+m)
  
  S.notices.push(m)
  var noticediv = $('div.notification').clone()
  
  $(noticediv)
            .attr('id','notice-clone')
            .attr('data-concern',m.concern)
  
  $(noticediv).find('small').html(m.time)
  $(noticediv).find('strong').html(m.concern)
  $(noticediv).find('i').html(m.message)
  $(noticediv).removeClass('hide').prependTo('div.notices')

  $('div#notice-clone').find('.btn-warning').click(filterNotice)
  $('div#notice-clone').find('.btn-danger').click(readNotice)
}

function filterNotice(e) {
  var div = e.target.closest('div')
  var notice = $(div).attr('data-concern')
  S.datatable.search(notice).draw()
}

function readNotice(e) {
  t = e.target
  var concern = $(t).closest('div').attr('data-concern')
  
  $.ajax({ url:'/api/notices/'+concern,
          type: 'POST'})

  $(t).closest('div').fadeOut() // sunset
}

function updateTotals() {
  $.ajax({ url:'/api/totals',
                   type: 'GET',
                success: function(data) {
                  S.totals = data
                  t = $('tr#totals')
                  
                  for(var field in ['devices','sessions','vendors','ssids'])
                    fadeSwap(t,'span.'+field, data[field])
                }
           })
  
}

function addTimer(name,code,timeout) {
  S.timers[name] = {'code': code, 'timeout': timeout}
  S.timers[name].timer = setInterval(code,timeout * 1000)
}

function delTimer(name) {
  try {
    timer = S.timers[name].timer
    clearInterval(timer)
  }
  catch (e) {
    console.log(e)
  }
}

function fadeSwap(that,them,newvalue) {
  var them = $(that).find(them)
  var oldvalue = $(them).html()

  if (oldvalue != newvalue) {
    $(that).find(them).fadeOut(1000,function() {
                                    $(this).fadeIn()
                                    $(this).html(newvalue)
                      })
  }
  return that
}

function updateStats() {
  $.ajax({ url:'/api/probestats',
                   type: 'GET',
                success: function(d) {
                  S.stats.push([
                                {key: 'day',
                                values: [ +new Date(), d.data.day ]},
                                {key: 'hour',
                                values: [ +new Date(), d.data.hour ]},
                                {key: 'minute',
                                values: [ +new Date(), d.data.minute ]},
                                {key: 'second',
                                values: [ +new Date(), d.data.second ]},
                                ])
                  
                  //if (S.charts.hasOwnProperty('nvgraph')) {
                  //  S.charts.nvgraph.update()
                  //}
                  
                  var stats = $('span.probestats')
                  var f = ['second','minute','hour','day','month']
                  
                  for(var i in f) {
                    fadeSwap(stats,'span#probes_per_'+f[i], d.data[f[i]])
                  }
                }
        })
  
  //addTimer('stats','updateStats()', 60)
}

function gridster() {
  if ( $('div.gridster').length )
   $(document).ready(function () {
    var gridData = localStorage.getItem('gridster')
  
    if(gridData!=null) {
      //console.log('Loading grid data! - ' + gridData.hashCode())


      $.each(JSON.parse(gridData), function(i,value) {
        var id_name
        id_name="#"
        id_name = id_name + 'row' + value.row + 'col' + value.col
        //console.log(id_name)
        $(id_name).attr({"data-col":value.col, "data-row":value.row, "data-sizex":value.size_x, "data-sizey":value.size_y})
      })
    }

      S.gridster = $(".gridster > ul").gridster({
        widget_base_dimensions: [400, 100],
        widget_margins: [0,0],
        min_cols: 2,
        min_rows: 2,
        max_cols: 5,
        max_rows: 5,
        center_widgets: false,
        shift_widgets_up: false,
        shift_larger_widgets_down: false,
				resize: { enabled: true },
        avoid_overlapped_widgets: true,
        collision: { wait_for_mouseup: true },
        /*serialize_params: function($w, wgd) {
            return {
                  id: $($w).attr('id'),
                  col: wgd.col,
                  row: wgd.row,
                  size_x: wgd.size_x,
                  size_y: wgd.size_y,
                 };
           },*/
        /*draggable: {
              stop: function(event, ui) {
                var data = JSON.stringify(this.serialize())
                localStorage.setItem('gridster', data)
                console.log('Updated localStorage - ' + data.hashCode())
              }
       },
       resizable: {
              stop: function(event, ui) {
                var data = JSON.stringify(this.serialize())
                localStorage.setItem('gridster', data)
                console.log('Updated localStorage - ' + data.hashCode())
              }
       }*/

      }).data('gridster').disable()
    });     
}

function toggleGridster() {
  if(S.gridsterEditable == 0) {
    S.gridster.enable();S.gridster.options.resize.enabled=1
    S.gridsterEditable = 1
  } else {
    S.gridster.disable();S.gridster.options.resize.enabled=0
    S.gridsterEditable = 0
  }
}

function getTypeahead() {
  setTimeout(function() {
    for ( var key in ['aps','probes','bts'] ) {
      for ( var d in S.overview[key] ) {
        d = S.overview[key][d]
        if ( d.hasOwnProperty('mac') )
          S.keys.push(d.mac)
        if ( d.hasOwnProperty('ssid') )
          S.keys.push(d.ssid)
        if ( d.hasOwnProperty('ssids') )
          d.ssids.forEach(function(ssid) { S.keys.push(ssid) } )
        if ( d.hasOwnProperty('vendor') )
          S.keys.push(d.vendor)
      }
    }
    S.keys = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.whitespace,
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        local: S.keys
        })
    
    $('#datatable_filter input').typeahead({ hint: true,
                                  minLength:1, },
                                { name: 'typeahead', source: S.keys })
  }, 5000)
}

function nvgraph(containerId, data) {
  nv.addGraph(function() {
      S.charts.nvgraph = nv.models.stackedAreaChart();
      //alert(S.charts.nvgraph)
      S.charts.nvgraph
       .x(function(d) { return d[0] })   //We can modify the data accessor functions...
       .y(function(d) { return d[1] })   //...in case your data is formatted differently.
       /*.useInteractiveGuideline(true)    //Tooltips which show all data points. Very nice!
       .rightAlignYAxis(true)      //Let's move the y-axis to the right side.
       .transitionDuration(501)
       .showControls(true)       //Allow user to choose 'Stacked', 'Stream', 'Expanded' mode.
       .clipEdge(true);*/
    
    S.charts.nvgraph.xAxis
       .tickFormat(function(d) { 
         return d3.time.format('%x')(new Date(d))
    });

    S.charts.nvgraph.yAxis
        .tickFormat(function(d)  { return d }); 

    d3.select(containerId)
              .datum(data)
              .call(S.charts.nvgraph)
  });
}
function dataUpdate() {
  if($('#datatable_length input').prop('checked')) {
    S.datatable.ajax.reload()
    //S.datatable.order([[6,'desc']]).draw()
  }
}

function regtable() {
  S.datatable = $('#datatable').DataTable({
          ajax: {
            url: '/api/regulars',
            method: 'GET',
          },
          autoWidth: true,
          paging: true,
          stateSave: true,
          colReorder: true,
          select: false,
          buttons  : ['colvis','csv','pdf','print'],
          pagingType: 'numbers',
    columns  : [
      {'data':'mac'},
      {'data':'vendor'},
      {'data':'sensors'},
      {'data':'sessions'},
      {'data':'ssids'},
      {'data':'firstseen'},
      {'data':'lastseen'},
      {'data':'tags'},
      {'data':'alltags'},
    ]
  })
}
function tailtable() {
  S.datatable = $('#datatable').DataTable({
          ajax: {
            url: '/api/tail',
            method: 'GET',
          },
          paging: false,
    columns  : [
      {'data':'mac'},
      {'data':'sensor'},
      {'data':'rssi'},
      {'data':'ssid'},
      {'data':'time'},
    ]
  })
    S.datatable.ajax.reload()
    S.datatable.order([[4,'asc']]).draw()

  if (typeof S.tailtimer == 'undefined')
    S.tailtimer = setInterval('S.datatable.ajax.reload()',2000)
}

function datatable() {
  if ( ! $('#datatable').length )
    return

  S.datatable = $('#datatable').DataTable({
        ajax: {
          url: '/api/overviewjson/'+$('input#minutes').val(),
          method: 'GET',
        },
        autoWidth: true,
        paging: true,
        stateSave: true,
        colReorder: true,
        select: false,
        dom: '<lBrfip<t>ip>',
        buttons  : ['colvis','copy','csv'],
        pagingType: 'numbers',
        responsive: {
            details: {
                type: 'column',
                target: '.details-control'
            }
          },
        columns  : [ { className: 'details-control',
                       orderable: false,
                       data: null,
                       defaultContent: ''},
                     {data:'sensors',
                      //render: function(d,t,r,m) { console.log(Object.keys(d)); return d }
                      },
                     {data:'mac',
                      /*render: function(d,t,r,m) {
                                    return '<a style="cursor:pointer" onclick=\'do_modal("mac","' + d + '")\'>' + d.replace(':','').substr(0,5) + '</a>'
                        }*/
                        },
                     {data:'vendor'},
                     {data:'lastrssi'},
                     {data:'probes'},
                     {data:'ssids'},
      //                render: '[, ]' },
                     {data:'lastseen'},
                     {data:'firstseen'},
                     {data:'sessioncount'},
                     {data:'tags',
                        orderable: false },
                   ],
        })

  
  
  /*S.datatable.on('draw.dt',function() {
    console.log('draw.dt')
  })

  S.datatable.on('init.dt',function() {
    console.log('init.dt')
  }) */
  
  S.datatable.on('xhr.dt',function ( e, settings, json, xhr ) {
    if(json.length)
			console.table(json)

		S.data = json.overview

		var div = $('.btn-group')[0]
		var	btns = $('button')
			
		S.data.tags.forEach(function(t) {
			if(btns.filter(function(s) {  return $(btns[s]).prop('id') == t } ).length)
				return

			var btndiv = $('<div>').addClass('btn-group tags').prop('role','button').prop('aria-label','...')
			var btn = $('<button>').prop('id',t).prop('type','button').addClass('btn btn-xs btn-info')
			
			btn.html(t)
			$(btn).appendTo(btndiv).appendTo(div)
		}) 
  	
		$('div.tags button').click(toggleTag)
	})
  
	
	S.datatable.on('processing.dt', renderTables)
   
  redrawOpt = $('<input type="checkbox" name="redrawOpt" value="redraw"> refresh <br>')
  
  redrawOpt.appendTo($('#datatable_length'))
  
  function delayUpdate() {
    S.datatable.ajax.url = "/api/overviewjson/"+1
    addTimer("dataUpdate","dataUpdate()",10)
  }
  
  setTimeout(delayUpdate,10000)

	reArrangeDT()

	drawDetails()
}

function renderTables() {
	S.probes = S.datatable.rows().data()
	rows = S.probes.length

	for(var i=0; i<=rows; i++) {
		var row = S.datatable.row(':eq('+i+')').data()
	
		if (typeof row != 'object')
			break
		if (!row.hasOwnProperty('mac'))
			break
		
		if (row['mac'].startsWith('<a'))
			continue
		
		var a = $('<a>').prop('id',row['mac']).addClass('mac')
		a.text(row['mac'].replace(/:/g,'').substr(0,5))

		row['mac'] = $(a).prop('outerHTML')

		if(row['ssids'].length) {
			ssids = row['ssids']
			for(var x=0;x<=ssids.length;x++) {
				if(typeof ssids[x] != 'undefined' && ssids[x].length) {
					if (ssids[x].startsWith('<a'))
						continue
					
					var a = $('<a>').prop('id',ssids[x]).addClass('ssid')
					a.text(ssids[x])
					$(a).attr('href','/lookup/ssid/'+ssids[x])
					$(a).attr('target','_new')
					row['ssids'][x] = $(a).prop('outerHTML')
				}
					
				S.datatable.row(':eq('+i+')').data(row)
			}
		}
	}


    $('a.mac').css('cursor','pointer')
              .on('click', function() {
                      do_modal('mac',$(this).prop('id'))
    })
   
    $('a.mac').each(function() {
      $(this).prop('title','Device: '+$(this).prop('id'))
    
  })
}

function reArrangeDT() {
	$('#datatable_filter,.dt-buttons.btn-group,#datatable_length').css('display','inline-block')
	$('#datatable_filter').css('width','40%')
	$('#datatable_filter').css('display','inline-block')
	
	$('#datatable_info').css('width','25%').css('align','center').appendTo($('.dt-buttons'))
}

function do_modal(type, q) {
  if(type == 'sensor') {
    $('.modal-body').load('/sensors', function(){
		$('#modal_sensors').modal({show:true})
    }) }
  else if (type == 'login') {
    $('#modal_login').modal({show:true})
    }
  else if (type == 'logout') {
    $('.modal-body').load('/logout', function(){
    $('#modal_logout').modal({show:true})
    }) }
  else if(type == 'mac') {
    $('.modal-body').load('/lookup/mac/'+q, function(){
    $('#modal_mac').modal({show:true})
    }) }
  else if (type == 'ssid') {
    $('.modal-body').load('/lookup/ssid/'+q, function(){
    $('#modal_ssid').modal({show:true})
    }) }
  else if (type == 'vendor') {
    $('.modal-body').load('/lookup/vendor/'+q, function(){
    $('#modal_vendor').modal({show:true})
  })
  }
}

function drawDateTime() {
  if(! $('#datetimepickerto').length)
    return
  
  $('#datetimepickerfrom').datetimepicker({ allowInputToggle: true,sideBySide:true,showTodayButton:true, })
  $('#datetimepickerto').datetimepicker({ allowInputToggle: true,sideBySide:true,showTodayButton:true, })
  $('#datetimepickerfrom').datetimepicker()
  $('#datetimepickerto').datetimepicker({ useCurrent: false  })
  $("#datetimepickerfrom").on("dp.change", function (e) {
    $('#datetimepickerto').data("DateTimePicker").minDate(e.date); })
  $("#datetimepickerto").on("dp.change", function (e) {
    $('#datetimepickerfrom').data("DateTimePicker").maxDate(e.date); })
  
  $('#datetimepickerfrom').data("DateTimePicker").date(new Date(new Date() - (30 * 1000 * 60)))
  $('#datetimepickerto').data("DateTimePicker").date(new Date())

  $('button#submitdate').on('click',function(d) {
    fromdate = $('#datetimepickerfrom input')[0].value
    todate = $('#datetimepickerto input')[0].value

    url = encodeURIComponent('fromdate='+fromdate+'&todate='+todate)

    window.location = '/overview?' + url
  })
}

function drawDetails() {
		return
    $('#example tbody').on('click', 'td.details-control', function () {
        var tr = $(this).closest('tr');
        var row = table.row( tr );
 
        if ( row.child.isShown() ) {
            // This row is already open - close it
            row.child.hide();
            tr.removeClass('shown');
        }
        else {
            // Open this row
            row.child( format(row.data()) ).show();
            tr.addClass('shown');
        }
    } );
}

/*function startCloud() {
  try {
    if(typeof window.ssidlist == 'undefined') {
      setTimeout('startCloud()',2000)
      return
    }
    
    window.ssidlist.forEach(function(d) { if(d.length) S.words.push({key: d, value: parseInt(Math.random(10) * 10)})})
    drawWordCloud(S.words)
  } catch {}
}*/

function sigmonInit() {
  console.log('Sigmon loading..')
  if (window.location.href.match('/tail'))
    return
  if (window.location.href.split('/')[3] == '')
    return

  //checkNotices()
  //updateTables()

  getSensors()
  getOwn()
  addTimer('updateTotals','updateTotals()',50)
  addTimer('updateStats','updateStats()',60)
  addTimer('getSensors','getSensors()',55)
  
  updateStats()
  updateTotals()
  resized()
  window.resize = resized

  if (window.location.href.match('/alert')) {
    console.log('alert')
    drawDataTables()
    drawTags()
  } else if (window.location.href.match('/data')) { // || window.location.href.match('/d')) {
    console.log('data')
    datatable() 
    drawTags()
  } else if(window.location.href.match('/regulars')) {
    console.log('regulars')
    //datatable() 
    gridster()
  } else if(window.location.href.match('/graphs')) {
    console.log('graphs')
    drawChart()
    eventDrops()
    nvgraph()
  } else {
    //drawDateTime()
    datatable()
    //drawDataTables()
    //drawTags()
    gridster()
    //startCloud()
  }
  //$('a').addClass('text-capitalize')
  
  //timeSelector()
  
  
  //eventDrops()
  //readDatas()
  //getTypeahead()

  //$('[data-toggle="popover"]').popover({content: popinfo})
  
  //setTimeout("nvgraph('#nvgraph',S.stats)", 2000)
  //['pre','div','span','ul','li','table','tr','td','thead'].forEach(function(t) { $(t).css('margin',0);$(t).css('padding',0)})
	S.log('Sigmon _version_ at your service.')

} 
