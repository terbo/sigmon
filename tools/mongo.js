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
  _id: 'lookup', value: function(q, i) {
  if ( /([A-Za-z0-9][A-Za-z0-9]:){3}/.test(q) ) { // client mac
    if( typeof i == 'undefined') { i = 15 } // minutes
    print(q,'\t',mac(q).next()['count'],'probes','\t"', ssids(q).next()['ssids'].sort().join('","')+'"')
    var last = session = start = db.clients.aggregate({$match: { mac: q }},{$sort: { time: -1 }}, {$limit: 1}).next()['time']
    for( ok=1; ; ok ++) {
      session = new Date(session - minute * i)
      try { last = db.clients.aggregate({ $match: { mac: q, time: { $lt: last, $gt: session }  }}).next()['time']}
      catch(e) { break }
    }
    print('\tenter:', last.toLocaleString(),
          '\texit:', start.toLocaleString(),
          '\tsessions:', ok,
          '\length:', parseInt((start - last) / 1000 / 60), 'minutes' ) 
  }
  else if ( q == /-/) { /* date */ }
  else { return db.clients.aggregate( { $match: {ssid: q } }, { $group: { _id: '$mac' , count: { $sum: 1} } }, { $sort: { count: -1 } }) }
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
  _id: 'ss', value: function(q,i) {
    if( typeof q == 'undefined') { q = 5 } // minutes
    last(q)['client'].forEach(function(doc){lookup(doc,i) })
  }
})
db.system.js.save({
  _id: 'now', value: function() {
    return new Date(ISODate())
  }
})

db.system.js.save({
  _id: 're', value: function() {
    print(load('mongo.js'))
  }
})
//db.system.js.save({
//  _id: '', value: function() {
//})
db.loadServerScripts()
