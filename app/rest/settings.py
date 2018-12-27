# add mongo database creation and indexing and validation here.

RESOURCE_METHODS = ['POST']

MONGO_DBNAME = 'sigmon'
MONGO_OPTIONS = {'tz_aware': True}

X_DOMAINS = '*'
MULTIPART_FORM_FIELDS_AS_JSON=True
DOMAIN = {
        'logs.sensors': {'allow_unknown': True},
        'aps': {'allow_unknown': True},
        'datapkts': {'allow_unknown': True},
        'bt': {'allow_unknown': True},
        'graphstore': {'allow_unknown': True,
                       'resource_methods':['GET','POST']},
          'probes': {
            'schema': {
              'mac': { 'type': 'string',
                      'required': True,
                      'maxlength':18,
                      'regex': '^(([A-Fa-f0-9][A-Fa-f0-9]:){5}[A-Fa-f0-9][A-Fa-f0-9])$', },
              'time': { 'required': True,},
              'rssi': { 'type': 'number',
                      'required': True,
                      'max': '-100', },
              'sensor': { 'type': 'string',
                      'required': True,},
              'seq': { 'type': 'integer',
                      'required': True,
                      'max': 4096,},
              'frame': { 'required': False,},
              'channel': { 'required': False,},
              'pktime': { 'required': False,},
              'ptime': { 'required': False,},
              'ptype': { 'required': False,},
              'ssid': { 'type': 'string',
                      'maxlength': 32, },
              'dst_mac': { 'required': False, 'type': 'string'},
              'version': { 'type': 'string', 'required': False},
          }
  },
}
          #'probes.hourly': {},
          #'fingerprints': {},
          #'probes.daily': {},
         # 'sessions': {},
         # 'vendors': {},
         # 'devices': {},
         # 'sensors': {},
         # 'ssids': {},
         # 'macs': {},
#         logs.sensors': {
#            'schema': {
#              'day': { 'type': 'datetime',
#                       'required': True,
#                     },
#              'sensor': { 'type': 'string',
#                       'required': True,
#                        },
#              'day.log': { 'type': 'dict',
#                'schema': {
#                  'runtime': { 'type': 'float',
#                               'required': True,
#                             },
#                  'memusage': {'type': 'integer',
#                              'required': True,
#                              },
#                  'errors': { 'type': 'list' },
#                          }
#                }
#              }
#            }
