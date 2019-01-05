#!/usr/bin/python

#import coloredlogs, logging
#from logging import error, debug, info

#coloredlogs.install()
from eve import Eve
app = Eve()
#import logging
#logging.basicConfig(level=logging.CRITICAL,
#                    format='%(asctime)s %(funcName)s %(threadName)s(%(lineno)d) -%(levelno)s: %(message)s')
 
if __name__ == '__main__':
  app.run(host='0.0.0.0',port=8989,debug=True,processes=4,threaded=False)
