#!/bin/bash
# v.001

cd $SIGMON_ROOT

PYTHON_ARGS='-uBRc'
SIGCODE='from app.sigmon import *;'
PPRINT='print(pp(%%()))'

CODE='run_workers()'

#stitle "[${0##*/}]"

while true; do
  RESULT=$( python $PYTHON_ARGS "$SIGCODE $CODE" )
  test -z $? && echo $? && sleep 10
  echo $RESULT | ccze -A
  sleep 120
done
