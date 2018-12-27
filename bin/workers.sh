#!/bin/bash
# v.001

# need to have this coordinate three background scripts
# devices runs every minute
# sessions every 4 minutes
# stats every 10

cd $SIGMON_ROOT

PYTHON_ARGS='-uBRc'
SIGCODE='from app.sigmon import *;'
PPRINT='print(pp(%%()))'

CODE='run_workers()'

#stitle "[${0##*/}]"

( while true; do python2.7 $PYTHON_ARGS "$SIGCODE run_worker('device')"; done ) &
sleep 1
( while true; do python2.7 $PYTHON_ARGS "$SIGCODE run_worker('session')";done ) &
sleep 1
( while true; do python2.7 $PYTHON_ARGS "$SIGCODE run_worker('stats')"; done ) &
