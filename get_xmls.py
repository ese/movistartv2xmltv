#!/usr/bin/env python
#Download raw xml data to inspect

# Stardard tools
import sys
import os
import re
import logging

from tva import TvaStream, TvaParser

logger = logging.getLogger('movistarxmltv')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('/tmp/movistar.log')
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

if len(sys.argv) == 2:
    IP = sys.argv[1]
    MCAST_PORT=3937
    print "Download xml files into /tmp/: "+IP
elif len(sys.argv) == 3:
    IP = sys.argv[1]
    MCAST_PORT = int(sys.argv[2])
else:
    print "Usage: "+ sys.argv[0]+' MULTICAST_GROUP [MULTICAST_PORT]'  
    exit()

logger.info("Getting xmls")

stream = TvaStream(IP,MCAST_PORT)
stream.getfiles()
for i in stream.files().keys():
    fM3u = open("/tmp/raw_"+IP+"_"+i+".xml", 'w+')
    fM3u.write(stream.files()[i])
    fM3u.close

exit()
