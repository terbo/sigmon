var ms = 1000, minute = ms * 60, hour = minute * 60, day = hour * 24

db.system.js.save( {
  _id: 'tail', value: function(num) {
    if( typeof num == 'undefined') { num = 5 }
    var total = db.clients.find().count()
    return db.clients.find().skip(total-num)
  }
})
db.system.js.save( {
  _id: 'top', value: function(field, dir) {
    if( typeof field == 'undefined') { field = 'mac' }
    if( typeof dir == 'undefined') { dir = -1 } else { dir = 1 }

    return db.clients.aggregate([{ $group: { _id: '$'+field, count: { $sum: 1 }}},{$sort: {'count': dir}}])
  }
})
db.system.js.save({
  _id: 'last', value: function(from, min, to, mod) {
    if( typeof from == 'undefined') { from = 5 } // minutes
    if( typeof min == 'undefined') { min = 2 } // probes
    if( typeof to == 'undefined') { to = 0 } // to date

    if( typeof mod == 'undefined') { mod = minute } else { mod = hour }

    res = db.clients.aggregate([
      { $match: { time: { $gt: new Date(ISODate().getTime() - mod * from)  }  } } ,
      { $match: { time: { $lt: new Date(ISODate().getTime() - mod * to)  }  } } ,
      { $sort: { time: -1 } },
      { $out: 'recents' } ] )

    return {
      results: db.recents.find().count(),
      from: db.recents.find().sort({'time':1})[0]['time'],
      to: db.recents.find().sort({'time':-1})[0]['time'],
      ssid: db.recents.distinct('ssid'),
      client: db.recents.distinct('mac'),
      sigmin: db.recents.aggregate({ $group: { _id: '$min', signal: { $min: "$signal"}}})['_batch'][0]['signal'],
      sigmax: db.recents.aggregate({ $group: { _id: '$max', signal: { $max: "$signal"}}})['_batch'][0]['signal']
    }
  }
})
db.system.js.save({
  _id: 'lookup', value: function(q) {
  if ( /:[A-Za-z0-9][A-Za-z0-9]:/.test(q) ) { // client mac
    var last = session = start = db.clients.aggregate({$match: { mac: q }},{$sort: { time: -1 }}, {$limit: 1}).next()['time']
    for( ok=0; ok < 10; ok ++) {
      session = new Date(session - minute * 10)
      last = db.clients.aggregate({$match: { mac: q, time: { $lt: start, $gt: session }  }})
      try { last = last.next()['time'] }
      catch(err) { break }
    }
    print('mac:',q, 'enter:', last, 'exit:', start) 
    //#return db.clients.aggregate({$match: { mac: q, time: { $lt: lastseen } } })
  }
  else if ( q == /-/) { }
  else { return db.clients.aggregate( { $match: {ssid: q } }, { $group: { _id: '$mac' , count: { $sum: 1} } }) }
  // return periods: seen in five minutes, until not seen, plus, time seen = session
  // re : mac - date else ssid
  }
})
db.system.js.save({
  _id: 'now', value: function() {
    return new Date(ISODate())
  }
})

db.system.js.save({
  _id: 'reload', value: function() {
    print(load('/root/code/sigmon/tools/mongo.js'))
  }
})
//db.system.js.save({
//  _id: '', value: function() {
//})
db.loadServerScripts()
