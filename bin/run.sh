#!/bin/bash

# also check services before launch
# check config, etc
# backup logs, check for updates . . . .

RUN_DIR='/tmp'

RUN_PIDFILE="$RUN_DIR/sigmon.run.pid"
PY_PIDFILE="$RUN_DIR/sigmon.python.pid"

CHECK_TIME=10

# minutes

[[ "$PATH" =~ '\b/sigmon' ]] || PATH="${SIGMON_ROOT}:$PATH"

cd $SIGMON_ROOT

timeu() {
  echo $(date '+%s')
}

timedt() {
  echo $(date '+%F %T')
}

timet() {
  echo $(date '+%T')
}

timed() {
  echo $(date '+%F')
}

LAST_CHECKED=$(timeu)

check_services() {
  MONGO=$(service mongodb status)
  return $?
}

runwebapp() {
  . ${SIGMON_ROOT}/etc/settings.sh
  python2.7 -uBR ${SIGMON_ROOT}/webapp.py &
  echo $! > $PY_PIDFILE
  
  if [ -z "${SIGMON_HTTPS}" ]; then
    python2.7 -uBR ${SIGMON_ROOT}/webappssl.py &
    echo "echo $! > $PY_PIDFILESSL"
  fi
}

stopwebapp() {
  PIDS=$(ps xaw | grep python2.7 | grep webapp.py | awk '{print $1}')
  for pid in ${PIDS//:/ };
  do
    echo -n "'$pid': $(kill ${pid})"
  done
  [ -f "$RUN_PIDFILE" ] && \
    pkill -e -F $RUN_PIDFILE && \
    rm -f $RUN_PIDFILE
  [ -f "$PY_PIDFILE" ] && \
    pkill -e -F "$PY_PIDFILE" && \
    rm -f "$PY_PIDFILE"

  sleep 1
  CHECK=$(ps xaw | grep --color=always -aHn -e webapp -e run.sh | grep -v grep)
  
  exit $?
}

check_sensors() {
  # good time for RESTy.
  SENSORS=$(cmd.sh active_sensors)
  TOTAL_SENSORS=$( cmd.sh -c 'len(list(db.sensors.find())' )

  if [ "${!SENSORS[#]}" -lt $TOTAL_SENSORS]; then
    for sensor in ${!SENSORS[*]}; do
      pingcheck
      sshcheck
      pythoncheck
      alert
    done
  fi
}


check_pids() {
  if [ -n "$1" ]; then
    for pidfile in $RUN_DIR/sigmon*pid; do
      echo "Checking $pidfile ..."
      pid=$(cat $pidfile)
      echo "$pid: $(pgrep $pid)"
    
    return $?
    done
  fi
  
  [ -f "$RUN_PIDFILE" ] && \
    [ -n "$(pgrep -F $RUN_PIDFILE)" ] || return 55
  [ -f "$PY_PIDFILE" ] && \
    [ -n "$(pgrep -F $PY_PIDFILE)" ] || return 33
  return 0
}

main_loop() {
  screentitle="sigmon "
  echo -e '\033k'$screentitle'\033\\'
  #(mosquitto_sub -t '#' -v | ccze -A) & 
  
  while true; do
  
    check_pids
    if [ $? = '0' ]; then 
      echo "Check if $0 is running, and remove stale pid files. - $PY_PIDFILE $RUN_PIDFILE"
      exit 1
    fi
    
    bin/rmpyc
    
    echo $$ > $RUN_PIDFILE
    trap stopwebapp EXIT
    coproc runwebapp

    sleep 5
    while check_pids; do 
      touch $RUN_PIDFILE
      sleep 5  # this is where all of the work is done.
    
      if [ "$(( $(timeu) - $LAST_CHECKED ))" -gt "$(( $CHECK_TIME * 60 ))" ]; then
        echo Stats for $(timedt)
        printf "   ["; for i in {1..$(( $COLS - 3))}; do printf '_'; done; echo ']'
        bin/cmd.sh probes_per_hour | ccze -A &
        bin/cmd.sh active_sensors  2>&1 > /dev/null 
        #wget -q --output-document=- http://1.0.0.1/api/overview &
        #printf "   ["; for i in {1..32}; do printf '_'; done; echo ']'
        wget -q --output-document=/dev/null http://1.0.0.1:8080/api/sensors/active | ccze -A &
        LAST_CHECKED=$(timeu)
      #elif [ "$(( $(timeu) - $LAST_CHECKED ))" -gt "$(( $WORKER_TIME * 60 ))" ]; then
      #  echo "Launching workers"
      #  wget -q --output-document=- http://1.0.0.1/api/workers &
      #  LAST_CHECKED=$(timeu)
      fi
    done
    
    for i in {1..10}; do
      echo -ne "\t$i $RANDOM $$\r"
      sleep 1
    done
  
  done
}

case "$1" in
 -c) check_pids -v ;;
 -k) stopwebapp ;;
  *) main_loop
esac
