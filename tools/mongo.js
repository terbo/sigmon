db.system.js.save( {
  _id: '_ms', value: function() {
  return 1000
  }
})
db.system.js.save( {
  _id: '_minute', value: function() {
  return _ms() * 60
  }
})
db.system.js.save( {
  _id: '_hour', value: function() {
  return _minute() * 60
  }
})
db.system.js.save( {
  _id: '_day', value: function() {
  return _hour() * 24 
  }
})
db.system.js.save( {
  _id: '_week', value: function() {
  return _day() * 7}
})
db.system.js.save( {
  _id: '_month', value: function() {
  return _week() * 4
  }
})
db.system.js.save( {
  _id: 'localtime', value: function() {
  }
})
db.system.js.save( {
  _id: 'localtime', value: function(obj) {
    if( typeof obj == 'undefined') { return new Date(0).toLocaleString() }
    return obj.toLocaleString() // test with hasProperty?
  }
})
db.system.js.save( {
  _id: 'tail', value: function(num) {
    // return last x probe inserts
    if( typeof num == 'undefined') { num = 5 }
    var total = db.clients.find().count()
    return db.clients.find().skip(total-num)
  }
})
db.system.js.save( {
  _id: 'top', value: function(field, dir) {
    // return highest / lowest totals of any field
    if( typeof field == 'undefined') { field = 'mac' }
    if( typeof dir == 'undefined') { dir = -1 } else { dir = 1 }

    return db.clients.aggregate([{ $group: { _id: '$'+field, count: { $sum: 1 }}},{$sort: {'count': dir}}])
  }
})
db.system.js.save({
  _id: 'last', value: function(from, min, to, mod) {
    // return last x minutes of unique probes/macs and min/max signal
    if( typeof from == 'undefined') { from = 5 } // minutes
    if( typeof min == 'undefined') { min = 2 } // probes
    if( typeof to == 'undefined') { to = 0 } // to date

    if( typeof mod == 'undefined') { mod = _minute() }
    else if ( ! mod in ['minute','hour','day','week','month'] ) { mod = _minute() }

    var res = db.clients.aggregate([
      { $match: { time: { $gt: new Date(ISODate().getTime() - mod * from)  }  } } ,
      { $match: { time: { $lt: new Date(ISODate().getTime() - mod * to)  }  } } ,
      { $sort: { time: -1 } },
      { $out: 'recents' } ] )
    return {
      results: db.recents.distinct('mac').length,
      from: localtime(db.recents.find().sort({'time':1})[0]['time']),
      to: localtime(db.recents.find().sort({'time':-1})[0]['time']),
      ssid: db.recents.distinct('ssid'),
      client: db.recents.distinct('mac'),
      sigmin: db.recents.aggregate({ $group: { _id: '$min', signal: { $min: "$signal"}}})['_batch'][0]['signal'],
      sigmax: db.recents.aggregate({ $group: { _id: '$max', signal: { $max: "$signal"}}})['_batch'][0]['signal']
    }
  }
})
db.system.js.save({
  _id: 'lookup', value: function(q) {
  // return ssid or mac information
  if ( /([A-Za-z0-9][A-Za-z0-9]:){3}/.test(q) ) { // client mac
    var session = sessions(q)
    f = firstlast(q).next() // better way..
    firstseen = f['first'], lastseen = f['last']
    if ( session.length < 2 ) {
      enter = exit = lastseen
      slength = 1
    } else {
      enter = session[0]['enter']
      exit = session[0]['exit']
      slength = parseInt(session[0]['duration'] / 1000 / 60)
    }
    
    return {
      mac: q,
      probes: mac(q).next()['count'],
      ssids: ssids(q).next()['ssids'],
      firstseen: localtime(firstseen),
      lastseen: localtime(lastseen),
      enter: enter,
      exit:  exit,
      length: slength
    }
  }
  else if ( q == /-/) { /* date */ }
  else { return db.clients.aggregate( { $match: {ssid: q } }, { $group: { _id: '$mac' , count: { $sum: 1} } }, { $sort: { count: -1 } }) }
  }
})
db.system.js.save({
  _id: 'firstlast', value: function(mac) {
    return db.clients.aggregate({$match: { mac: mac} }, {$group: {_id: "$mac", first: { $min: "$time" }, last: { $max: "$time"} }}, {$sort: { last: 1} })
  }
})
db.system.js.save({
  _id: 'ssids', value: function(q) {
    return db.clients.aggregate(
      { $match: { mac: q } },
      { $group: { _id: '$mac', ssids: { $addToSet: "$ssid"} } })
  }
})
db.system.js.save({
  _id: 'mac', value: function(q) {
    return db.clients.aggregate(
      { $match: { mac: q } },
      { $group: { _id: '$mac', count: { $sum: 1 } }})
  }
})
db.system.js.save({
  _id: 'ss', value: function(q) {
    if( typeof q == 'undefined') { q = 5 } // minutes
    var out = new Array()
    last(q)['client'].forEach(function(doc){out.push(lookup(doc)) })
    return out
  }
})
db.system.js.save({
  _id: 'now', value: function() {
    return new Date(ISODate())
  }
})

db.system.js.save({
  _id: 're', value: function() {
    load('mongo.js')
  }
})
db.system.js.save({
  _id: 'sessions', value: function(mac, range, limit) {
    var lastseen, i = 0
    var sessions = new Array(), session = new Array()

    if ( typeof range == 'undefined') { range = lastseen = firstlast(mac).next()['latest'] }
    else { lastseen = range }
    if ( typeof limit == 'undefined') {limit = 10 }

    db.clients.find({mac:mac}).sort({time:-1}).forEach(function(doc){
      if(doc['time'] < lastseen - (_minute() * 5)) {
        i += 1
        if( i >= limit) { return }
        if(session.length > 1) {
          sessions.push({enter:localtime(lastseen),
            exit:localtime(session[0]),
            duration:session[0] - lastseen})
          session = []
        } else { // kludge
          session.push(doc['time'])
        }
      } 
      lastseen = doc['time']
    })
    return sessions
  }
})
db.system.js.save({
  _id: 'disco', value: function() {
  return db.drones.find({$or: [{connected:false}, {lastseen: { $lt: new Date(new Date().setSeconds(now().getSeconds()-15)) } }]})
  }
})
db.system.js.save({
  _id: 'drones', value: function() {
  return db.drones.find({},{info:true,lastseen:true,iface:true,connected:true,name:true,'ssh.ip':true,'ssh.port':true,_id:false}).pretty()
  }
})
//db.system.js.save({
//  _id: '', value: function() {
//})
db.loadServerScripts()
