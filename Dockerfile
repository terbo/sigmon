# base image
FROM debian:7-slim

# set working directory
RUN mkdir /usr/src/sigmon
RUN mkdir -p /data/sigmon
WORKDIR /usr/src/sigmon

# We're going to need this during setup
ADD . /usr/src/sigmon

#install software dependencies
RUN apt-get update
RUN apt-get -y install iw wireless-tools libpcap-dev tcpdump mongodb-clients ntpdate macchanger screen htop discus \
    wget gcc cpp g++ make mosquitto-clients python2.7 python-pip python-pcapy python-bson 
    
# We'll be installing impacket through pip later, so explicitly remove it here
RUN apt-get -y remove python-impacket

# Older versions of pip and distribute default to http://pypi.python.org/simple, which no longer works. The following
# will update pip to use https.
RUN pip install -i https://pypi.python.org/simple -U pip distribute

# Install PIP dependencies
RUN pip2.7 install -r /usr/src/sigmon/etc/requirements.txt
