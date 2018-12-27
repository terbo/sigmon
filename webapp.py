#!/usr/bin/env python2.7

import coloredlogs, logging
coloredlogs.install()

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(funcName)s %(threadName)s(%(lineno)d) -%(levelno)s: %(message)s')
#logging.basicConfig(level=logging.DEBUG,
#                   format='%(asctime)s %(levelname)s : %(message)s')

from app import app, views

def main():
  app.run(
          host='0.0.0.0',
          port=8080,
          #ssl_context=('etc/ssl/dev.sigmon.net.crt','etc/ssl/dev.sigmon.net.key'),
          debug=True,
          threaded=False,
          processes=5)

if __name__ == '__main__':
  main()
