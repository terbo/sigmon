#!/bin/bash
# v.001

cd /data/sigmon

PYTHON_ARGS='-uBRc'
SIGCODE='from app.sigmon import *;'
PPRINT='print(pp(%%()))'

case "$1" in
  '') echo 'cmds: '; exit 22 ;;
  -c) shift; CODE="$@" ;;
   *) CODE="print(pp(${@}()))" ;;
esac

screentitle="$1"
echo -e '\033k'$screentitle'\033\\'

RESULT=$( python2.7 $PYTHON_ARGS "$SIGCODE $CODE" )

echo $RESULT
