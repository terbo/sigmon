#!/usr/bin/pyton

from functools import wraps
from flask import Flask, abort, jsonify #, session, Session
from flask import render_template, request, redirect, url_for
from flask import Response, stream_with_context

from flask_bootstrap import Bootstrap #, StaticCDN
from werkzeug import secure_filename
from werkzeug.routing import BaseConverter
from urllib import unquote_plus
from os import system
#from flask.ext.session import Session

from app.sigmon import *
from app import app

#SESSION_TYPE = 'mongodb'
#SESSION_MONGODB = '1.0.0.1'
#SESSION_MONGODB_DB = 'sigmon'
#SESSION_MONGODB_COLLECT = 'access.sessions'

#app.config.from_object(__name__)
#Session(app)

#app.config.setdefault('BOOTSTRAP_SERVE_LOCAL', True)
Bootstrap(app)
#app.extensions['bootstrap']['cdns']['jquery'] = StaticCDN()

app.jinja_env.line_statement_prefix = '%'

class RegexConverter(BaseConverter):
  def __init__(self, url_map, *items):
    super(RegexConverter, self).__init__(url_map)
    self.regex = items[0]

app.url_map.converters['regex'] = RegexConverter

def auth(f):
  @wraps(f)
  def checkauth(*args,**kwargs):
    return f(*args, **kwargs)
    if session:
      if session.has_key('authenticated'):
        #if session['authenticated'] in authenticated_sessions:
        debug('auth session')
        return f(*args, **kwargs)
    else:
      debug('new session')
      return redirect(url_for('index',next=request.url))
  return checkauth

# have a javscript that marks load and updates time_out??
def loghit(f):
  @wraps(f)
  def log_hit(*args, **kwargs):
    db.logs.web.insert_one({
      'useragent': request.headers.get('User-Agent'),
      'url': request.url_rule.rule,
      'remote_ip': request.remote_addr,
      'time_in': time.time(),
      'request_type': request.method,
      'request_uri': request.access_route[0],
      'request_host': request.host,
      'time_in': dt.now(),
      'remote_user': request.remote_user,
    })
    return f(*args, **kwargs)
  return log_hit

@app.route('/d3', methods=['GET'])
def d3view():
  return render_template('d3.html', display=['datatable'])

@app.route('/d3g', methods=['GET'])
def d3gview():
  return render_template('d3g.html', display=['datatable'])

@app.route('/login', methods=['GET','POST'])
def login():
  if request.method == 'POST':
    try:
      username = request.form['username']
      password = request.form['password']
      debug(username)
    
      if db.settings.find_one({'name':username,'password':password}):
        debug('*** woot. ***')
        session['authenticated'] = True
        session['user'] = username
    except:
      pass
    return redirect(url_for('index'))
  else:
    return render_template('modal/login.html')

@app.route('/line',methods=['GET'])
def hmmm():
    return render_template('line.html')

@app.route('/',methods=['GET'])
@app.route('/o',methods=['GET'])
@app.route('/o/<int:mins>',methods=['GET'])
@app.route('/overview',methods=['GET'])
@app.route('/overview/<int:mins>',methods=['GET'])
@loghit
def index(mins=5,tags=[]):
  url = request.url_rule.rule.replace('/','')
  if url == '': #session and 'authenticated' not in session:
  #  display = ['splash','gridster']
  #  data = re.sub('%s/app' % SIGMON_ROOT,'',
  #              random.choice(glob.glob('%s/app/static/bg/small*' % SIGMON_ROOT)))
    display = ['splash','gridster']

    data = re.sub('%s/app' % SIGMON_ROOT,'', random.choice(glob('%s/app/static/img/bg/*' % SIGMON_ROOT)))
    tmpl = 'splash.html'
    
    return render_template(tmpl, display=display,data=data)
  #else:
    #data = {'totals': {'ssids': 1}}#overview(mins)
  #  ua = request.headers.get('User-Agent')
    
    #if re.match('(Wget|w3m|lynx|curl)',ua) or request.args.get('txt'):
    #  tmpl = 'overview.txt'
    #else:
    
  #if url.startswith('overview'):
  #    req = request.url
  #    args = unquote_plus((req.split('?'))[1]).split('&')
  #    args[0] = args[0].split('=')[1]
  #    args[1] = args[1].split('=')[1]
  #    
  #    fromdate  = dateutil.parser.parse(args[0])
  #    todate   = dateutil.parser.parse(args[1])
  #    mins = ((todate - fromdate).seconds) / 60
  #    data = overview(mins,start=fromdate)
  #    debug('Start: ' + args[0] + ', End: ' + args[1])
  #else:
  
  
  #['/',''] or url.startswith('index') or
  if url.startswith('o') or url.startswith('overview'):
    tmpl = 'overview.html'
  elif url.startswith('bluetooth') or url.startswith('bt'):
    tmpl = 'overview/bt.html'
  elif url.startswith('ap'):
    tmpl = 'overview/aps.html'
  elif url.startswith('probes') or url.startswith('wifi'):
    tmpl = 'overview/probes.html'
  
  data = overview(mins,getprobes=False)
  
  display = ['datatable','stats','probeview']# db.access.find_one({'name':session['user']})['display']

  return render_template(tmpl,
                         mins=mins,
                         data=data,
                         display=display,
                         ssids=data['ssids'],
                         version='0.9-dev')


@app.route('/search',methods=['GET'])
def searchG():
    return render_template('s.html')

@app.route('/api/tag',methods=['GET'])
def tagApi():
  return

@app.route('/d',methods=['GET'])
@app.route('/d/<int:mins>',methods=['GET'])
@app.route('/data',methods=['GET'])
@app.route('/data/<int:mins>',methods=['GET'])
def datapage(mins=5):
  data = overview(mins)
  display = ['datatable']
  tmpl = 'data.html'
  
  #for p in range(0, len(data['probes'])):
  #  debug(data['probes'][p]['mac']) # = "<a onclick='do_modal(\"mac\",\"%s\")'>%s:%s</a>" % (p['mac'], p['mac'], p['vendor'])
  #  
  #  for s in range(0,len(p['ssids'])):
  #    data['probes'][p]['ssids'][s] = "<a onclick='do_modal(\"%s\")'>%s</a>" % (s, s)

  return render_template(tmpl,
                      mins=mins,
                      data=data,
                      display=display,
                      version='0.9-dev')

@app.route('/api/owndevs',methods=['GET'])
@app.route('/api/owndevs/<mac>', methods=['POST','GET'])
@app.route('/api/owndevs/<mac>/<name>', methods=['POST','GET'])
def getownApi(mac=None, name=None):
  if mac: #if request.method == 'POST':
    try:
      query = {'$addToSet': {'tags': 'owned'} }
      if name:
        info(str(name))
        info('Setting name of "%s" to "%s"' % ( mac, name))
        query.update({'$set': {'name': name}})

      info(query)
      db.devices.find_one_and_update({'mac': mac}, query)
      return OK(1)
    except Exception as e:
      info(e)
      return OK(0)
  else:
    return jsonify({'data':owndevs()})

@app.route('/api/regulars',methods=['GET'])
def regularApi():
    return jsonify({'data':regulars()})

@app.route('/regulars',methods=['GET'])
def regularpage():
  tmpl = 'regulars.html'
  return render_template(tmpl)

@app.route('/cloud',methods=['GET'])
def d3cloud():
    return render_template('cloud.html')

@app.route('/api/locatable',methods=['GET'])
def locatableApi():
    data = locatable()
    return jsonify({'data': data})

@app.route('/api/aps',methods=['GET'])
@app.route('/api/aps/<mins>',methods=['GET'])
def aplistapi(mins=15):
    out = aplist(mins)
    return jsonify(out)

@app.route('/api/ssids',methods=['GET'])
def ssidlist():
    ssid = []
    ssids = list(db.ssids.find({},{'_id':False}))
    types = {'ISP': {'^BHN.*','^ATT.*','^2WIRE.*','^NETGEAR.*','^linksys.*','^ARRIS.*','^MySpectrumWifi.*','^belkin.*'},
     	     'PLACE': {'KHSD.*', '^Taco Bell.*','^Walmart.*','.*Burger.*','.*Pizza.*'},
	     'HOTSPOT': {'.*iphone.*','^Samsung.*','^LG.*'}
	    }

    for s in ssids:
    	ssid.append({'key': s['ssid'], 'value': len(s['mac']) })
    
    #for i in ssid:
    #  for t in types:
    #    for s in types[t]:
#	  if(re.match(s, i['key']) != None):
#            i['type'] = t
    
    return jsonify(ssid)

@app.route('/alert',methods=['GET'])
def alertpage():
  mins=2
  data = overview(mins)
  display = ['stats','probeview','datatable']
  tmpl = 'alert.html'
  return render_template(tmpl,
                      mins=mins,
                      data=data,
                      display=display,
                      version='0.9-dev')

@app.route('/map',methods=['GET'])
def perimap():
  tmpl = 'map.html'
  data = overview(15)
  display = ['datatable','stats','probeview']
  
  return render_template(tmpl, display=display,
                         data=data,mins=15)

@app.route('/graphs',methods=['GET'])
def allgraphs():
  return render_template('graphs.html')

@app.route('/graph',methods=['GET'])
def dgraph():
  return render_template('graph.html',
                display=['d3graph','datatable','slider2'])

@app.route('/play',methods=['GET'])
def playgraph():
  return render_template('play.html')

@app.route('/play2',methods=['GET'])
def playgraph2():
  return render_template('play2.html')

@app.route('/tail', methods=['GET'])
def tailf():
    return render_template('tail.html')

@app.route('/api/tail', methods=['GET'])
@app.route('/api/tail/<int:num>',methods=['GET'])
@app.route('/api/tail/since/<int:num>',methods=['GET'])
def tailapi(num=50,since=False):
  p = taildb(int(num),since=float(since))
  return jsonify({'data':p})

@app.route('/api/overviewjson',methods=['GET'])
@app.route('/api/overviewjson/<mins>',methods=['GET'])
@loghit
def overviewJson(mins=1): #,tags=[]):
  output = overview(mins)
  return jsonify({'data':output['probes'], 'overview': output})

@app.route('/api/overview',methods=['GET'])
@app.route('/api/overview/<mins>',methods=['GET'])
@app.route('/api/overview/<mins>/<tags>',methods=['GET'])
@loghit
def overviewApi(mins=1,tags=[]):
  output = overview(mins,tags)
  return jsonify({'data': output})

@app.route('/api/notices',methods=['GET'])
@app.route('/api/notices/<concern>',methods=['POST'])
@loghit
@auth
def noticeApi(concern=False):
  if request.method == 'POST':
    notice(concern,markread=True)
    return OK(1)
  else:
    n = get_notices()
    if n:
      for m in n:
        ts = m['time']
        m.update({'time': ts.astimezone(TZ).strftime('%F %T')})
      return jsonify({'data':n})
    else:
      return OK(0)


@app.route('/api/totals',methods=['GET'])
@loghit
@auth
def totalsApi():
  totals = totalstats()
  return jsonify({'data':totals})

@app.route('/api/eventgraph',methods=['GET'])
@loghit
@auth
def eventgraphApi():
  graph = eventgraph()
  
  return jsonify({'data': graph})

@app.route('/api/heatmap')
@loghit
def heatmapApi():
  h = heatmap()
  return jsonify({'data': h})

@app.route('/api/graph',methods=['GET'])
@app.route('/api/graph/<what>',methods=['GET'])
@app.route('/api/graph/<what>/<when>',methods=['GET'])
@app.route('/api/graph/<what>/<when>/<howlong>',methods=['GET'])
@loghit
#@auth
def graphApi(what='probes',when=1,howlong=1):
  graph = graphdata(time=dt.now() - timedelta(days=int(when)), hours=int(when)*int(howlong))
 
  #debug(jsonify(graph))
  #hours = ['hours']
  #probes = ['probes']
  
  #for hour in graph.keys():
  # hours.append(hour)
  # probes.append(graph[hour])

  if what == 'vendors':
      res = graph['seen_vendors']
  elif what == 'daily':
    res = {'day': graph['daily_graph'],
           'probes': graph['daily_probes'],
           'new_devices': graph['new_devs_hourly'],
           'sessions': graph['sessions_hourly'] }
  elif what == 'hourly':
    res = {'hour': graph['hourly_graph'],
           'probes': graph['hourly_probes'],
           'new_devices': graph['new_devs_hourly'],
           'sessions': graph['sessions_hourly'] }
  else:
    abort(400)
  
  return jsonify(res)

##
#   Admin
##

@app.route('/devs',methods=['GET','POST'])
@app.route('/devices',methods=['GET','POST'])
@loghit
@auth
def viewdevices():
  data = active_sensors(return_all=True)

  devs = owndevs()

  return render_template('devices.html',
                        sensors=data,
                        owndevs=devs)

@app.route('/config',methods=['GET','POST'])
@loghit
@auth
def webconfig():
  pass 

@app.route('/sensorlogs')
@loghit
@auth
def sensorlogs():
  out = list(db.logs.web.find().limit(100).sort([('time',-1)]))
  cols = lsdb(False)
  return render_template('collections.html',
                      title='logs.sensors',
                      col=out)

@app.route('/weblogs')
@loghit
@auth
def weblogs():
  out = list(db.logs.web.find().limit(100).sort([('time',-1)]))
  return render_template('collections.html',
                      title='logs.web',
                      col=out)

@app.route('/joblog')
@loghit
@auth
def joblogs():
  out = list(db.logs.jobs.find().limit(100).sort([('time',-1)]))

  return render_template('collections.html',
                      title='logs.jobs',
                      table=out)
##
#  API / JSON
##

@app.route('/api/help')
def helpApi():
  routes = []
  for line in open('/data/sigmon/app/views.py').readlines():
    if(line.startswith('@app.route')):
      routes.append(line)
  
  return render_template('routes.html', data=sorted(routes))

@app.route('/api/sessions/<q>',methods=['GET'])
@loghit
@auth
def sessionsApi(q):
  return jsonify(get_sessions(q))

  #n = sorted(sensors, key=lambda x: sensors[x]['status'].has_key('connected') and sensors[x]['status']['connected'])
  #for sensor in list(reversed(n)):

# returns list of active sensors or full db
@app.route('/api/sensors',methods=['GET','POST'])
@app.route('/api/sensors/<q>',methods=['GET','POST'])
@loghit
def sensorsApi(q='active'):
  sensors = active_sensors()
  if q == 'active':
    return jsonify({'data':sensors})
  
  elif q == 'full':
    data = active_sensors(return_all=True)
    
    return jsonify({'data': data})
 
  #elif q == 'locate' and request.method == 'GET':
  elif q == 'locate' and request.method == 'POST':
    ret = ''
    try:
      data = request.form
      loc = [data['lat'], data['lng']]
      ret = db.sensors.update_one({'name': data['name']}, {'$set':
        {'longlat.coordinates': loc }})
    except Exception as e:
      debug('Updating sensor %s: %s (%s)' % ( data, ret, e) )
    finally:
      return OK(1)

  elif q == 'edit' and request.method == 'POST':
    info('Editing..')
    s = request.form
    # need to add .change and .errors, but grepping the update
    # for .error classes ...
    # Add a sensor
    # sensor stats
    #  total uptime (first probe - gaps - last probe)
    #  total probes
    #  average/min/max rssi
    #  ssids?
    #  
    # then .. datatables with search options,
    # which get sent to the api and executed ...
    #
    #for key in s.keys():
    
    try:
      (ip,port) = s['ssh'].split(':')
      (user,ip) = ip.split('@')
    except:
      (ip,user,port) = ('0.0.0.0','root',22)

    sensor =  {'name': s['name'],
              'info': { 'desc': s['desc'],
                        'serial': s['serial'],
                        'notes': s['notes'],
                        'brand': s['brand'],
                        'model': s['model'],
                        'os':    s['os'],
                        'ip':    ip,
                      },
              'location': s['location'],
              'ssh': { 'port': port,
                       'user': user,
                       'auth': 'key',
                       'gzip': True,
                     },
             }
    
    info(sensor)
    
    try:
      ret = db.sensors.update_one({'name': s['name']}, {'$set': sensor})
      info(ret)
      return OK(1)
    except Exception as e:
      info(e)
      return OK(0)
  else:
    sensorname = q
    ret = db.sensors.find({'name': sensorname},{'_id': False})
    
    if ret.count():
      return jsonify({'data':ret[0]})
  
  abort(400)


# returns vendor name search
@app.route('/vendor/<q>',methods=['GET'])
@app.route('/api/vendor/<q>',methods=['GET'])
@loghit
@auth
def vendorApi(q):
    res = []
    for vend in db.vendors.find({'name':q},{'_id': False}):
        res.append(vend)
    return jsonify(res)

# returns mac/ssid client info
@app.route('/lookup/<q>',methods=['GET'])
@app.route('/lookup/<typ>/<q>',methods=['GET'])
@loghit
@auth
def lookupapi(q,typ='mac'):
    if re.match(r'(?:[0-9a-fA-F]:?){12}',typ) or typ == 'mac':
        data = lookup(q)
        tmpl = 'lookup-mac.html'
        try:
          info=data[q]['info'][0]
        except:
          info=data[q]['info']
    
        return render_template(tmpl,
                               mac=q,
                               info=info,
                               totalprobes=data[q]['totalprobes'],
                               probes=data[q]['probes'],
                               sessions=data[q]['sessions'],
                               data=data)
    elif typ == 'ssid':
        data = lookup(q)
        tmpl = 'lookup-ssid.html'
        totalprobes = 0
        for mac in data:
            totalprobes += mac['count']
        
        vendor = vendor_oui(q)

        return render_template(tmpl,
                               name=q,
                               bssid='00:00:00:00:00:00',
                               data=data,
                               vendor=vendor,
                               totalprobes=totalprobes)
    elif typ == 'oui':
        return jsonify({'data': {'mac': q, 'vendor': vendor_oui(q)}})

    elif typ == 'vendor':
        search = re.compile('.*'+q+'.*',re.IGNORECASE)
        res = list(db.vendors.find({'name': {'$regex': search}},{'_id':False}))
        return jsonify(res)

    abort(400)

@app.route('/api/lookup/<q>',methods=['GET'])
@loghit
@auth
def apimac(q):
  return jsonify({'data': lookup(q)})

##
# Sensor interface
##

@app.route('/api/whosaw/<mac>',methods=['GET'])
@app.route('/api/whosaw/<mac>/<since>',methods=['GET'])
@loghit
@auth
def whosawApi(mac,since=1):
  mac = re.sub('_',':',mac)
  ret = whosaw(mac)
 
  ret['probes'] =  taildb(100,since,False,mac) 
  return jsonify(ret)

@app.route('/api/probestats', methods=['GET'])
@app.route('/api/probestats/<what>', methods=['GET'])
@loghit
@auth
def probestatsApi(what='hourly'):
  if what == 'hourly':
    pph = probes_per_hour()
    return jsonify({'data': pph })
  elif what == 'monthly':
    ppm = probes_per_month()
    return jsonify({'data': ppm })



# allows POST entries - use SSH auth?
@app.route('/api/upload',methods=['POST','PUT'])
def uploadApi():
  #vrfy sensor ip and name
  if 'Sensor' in request.headers: # and 'APIKey' in request.headers:
    content_type = request.headers['Content-Type']
    sensor = request.headers['Sensor']
    #apikey = request.headers['APIKey']
    postfrom = request.remote_addr

    if content_type == 'multipart/form-data':
      length = request.content_length
      data = request.stream.read();
      filename = secure_filename(request.headers['Original-Filename'])
   
      if len(data) != length:
        abort(405)
      
      #debug("Received file '%s' (%s bytes) from %s (%s)" % ( filename, length, postfrom, sensor ))
      savecap(filename, data)
      return OK(1)
    elif content_type == 'application/json':
      data = request.get_json()
      #debug("Received JSON (%s elements) from %s (%s)" % ( len(data), postfrom, sensor ))
      addpacket(data)
      return OK(1)
    # simple standalone reciever - eve or flask listen, submit to mongo, bout it 
  
  abort(403)


def OK(ok=1):
  if ok == 1:
    return jsonify({'result':True})
  else:
    return jsonify({'result':False})

@app.route('/cols',methods=['GET','POST'])
@app.route('/cols/',methods=['GET','POST'])
@app.route('/cols/<db_lookup>',methods=['GET','POST'])
@app.route('/cols/<db_lookup>/<rlimit>',methods=['GET','POST'])
@loghit
def dbApi(db_lookup='logs.jobs',rlimit=250,since=False):
  if request.method == 'POST':
    pass
  else:
    #db_lookup = request.args.get('db_lookup')
    if db_lookup in db.collection_names():
      size = 0
      fields=[]
      
      rows = dbdump(db_lookup,rlimit)
  
      for field in rows[0]:
        fields.append(field)
       
      cols = lsdb(False)
      for col in cols:
        size += int(cols[col])

      return render_template('collections.html',
                              title=db_lookup,
                              size=size,
                              col=rows,
                              cols=cols,
                              fields=fields,
                              display=['datatable'])

# tracking logic:
# phone sends request to be tracked
#  (every 4 seconds)
#   POST /api/track
#   DATA mac, host, gps location
# * host is translated to mac
#   you're only tracking own devices
#
# Then loads URL /track/mac
# this page displays Leaflet map,
# and GETs last seen probes
# (every 5 secs)
# Displayed in browser is last signal levels
# Recorded in db.fingerprints is all above

# print perimap template
# ask for posters loc
# send signals and location of sensors
@app.route('/track/<mac>',methods=['GET'])
def viewtrack(mac):
  trackres = trackview(mac)
  return render_template('track.html',
                         title='tracking: %s' % mac,
                         mac=mac, track=trackres)

@app.route('/api/track',methods=['POST'])
@app.route('/api/track/<mac>',methods=['GET'])
def apitrack(mac=None):
  if request.method == 'POST':
    #mac = request.form['mac']
    loc = request.form['loc']
    host = request.form['host']
    trackadd(host,loc)
    return jsonify({'data': True})
  elif request.method == 'GET':
    #mac = request.args.get('mac')
    return jsonify({'data':trackview(mac)})

@app.template_filter('strftime')
def _jinja2_filter_datetime(date, fmt='%D %T'):
    return dt.strftime(date,fmt)

@app.template_filter('commify')
def _jinja2_filter_number(number):
    return commify(number)
    
def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv

@app.route('/set/')
def set():
    session['key'] = 'value'
    return OK(1)

@app.route('/get/')
def get():
    return session.get('key', 'not set')

@app.route('/leds', methods=['GET'])
def ledpage():
  return render_template('leds.html')

@app.route('/api/leds/<int:ledset>', methods=['POST'])
def setleds(ledset=1):
  r = request.form['r']
  g = request.form['g']
  b = request.form['b']
  #debug('%s, %s, %s' % ( r, g, b))

  mqtt.publish('/LED/%d' % ledset, '%s,%s,%s' % (r,g,b))

  return OK(1)

# vim: set ts=2 sw=2 ai expandtab softtabstop=2
