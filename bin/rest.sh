#!/bin/bash

#screentitle="[${0##*/}]"
#echo -e '\033k'$screentitle'\033\\'

cd ${SIGMON_ROOT}/app/rest
python2.7 api.py
