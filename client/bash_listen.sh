#!/bin/bash 

VERSION=0.003

# add channel hopper

# perhaps add this into the daemon script and
# take commands, ec wget /api/commands/$sensor
# but ... how did that guy get that probr console working!?

# save files in x second intervals

[ -z "$LISTEN_TIME" ] && LISTEN_TIME=15
[ -z "$POST_URL" ] && POST_URL='http://1.0.0.1:8080/api/upload'
[ -z "$FILTER" ] && FILTER='type mgt and subtype probe-req'
[ -z "$IFACE" ] && IFACE='wlan1mon'
[ -z "$ARGS" ] && ARGS="-q -s 0 -e -n -G ${LISTEN_TIME}"
[ -z "$FMT" ] && FMT="$(uname -n)_${IFACE}_%F_%H-%M-%S-%Z.cap"
[ -z "$OUT" ] && OUT="/tmp/new/out"
[ -z "$IN" ] && IN="/tmp/new/in"


PIDFILE=/tmp/sigmon/listen.pid

[[ ! -f "/tmp/sigmon" ]] && mkdir /tmp/sigmon

mkdir -p ${OUT}
mkdir -p ${IN}

stop_tcpdump() {
  kill $COPROC_PID
}

start_tcpdump() {
  echo $$ > $PIDFILE
  
  coproc $(which tcpdump) ${ARGS} -i "${IFACE}" -w "${IN}/${FMT}" "${FILTER}"
  trap stop_tcpdump EXIT
}

while true; do
  #check_interface
  #check_update
  start_tcpdump
  
  while [[ "$COPROC_PID" -gt 0 ]]; do
    touch -a $PIDFILE

    sleep 1
    for file in ${IN}/*.cap; do
      if [ -f "$file" ]; then
        OPENED=$(ls -l /proc/${COPROC_PID}/fd | grep "${file}")
        test -z "${OPENED}" && mv $file $OUT
      fi
    done
    sleep 1
    for file in ${OUT}/*.cap; do
      if [ -f "$file" ] && [ -s "$file" ]; then
        filename=$(basename $file)
        echo wget -q \
           --output-document=- \
           --header 'Content-type: multipart/form-data' \
           --header "Sensor: $HOSTNAME" \
           --header "Original-Filename: ${filename}" \
           --header "Filetype: PCAP" \
           --post-file ${file} -- $POST_URL && rm -f ${file}
        if [ -f "$file" ]; then
          echo "UNABLE TO UPLOAD '$file' - FIX"
        fi
        sleep .5
      fi
    done

    sleep $(( $LISTEN_TIME / 2 ))
  done
done
