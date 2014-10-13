#!/usr/bin/env python
# TO DO:
# - Fixing encoding and parsing issues
# - Adding tv_grab standard options
# - Using a temporary file to save user province, channels and epg days, so we save time in each execution

# Stardard tools
import sys
import os
import re
import logging

# Time handling
import time
import datetime
from datetime import timedelta

# XML
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, Comment, ElementTree

from tva import TvaStream, TvaParser

logger = logging.getLogger('movistarxmltv')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('/tmp/movistar.log')
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

reload(sys)

SOCK_TIMEOUT = 3
MCAST_GRP_START = '239.0.2.129'
MCAST_PORT = 3937
MCAST_CHANNELS = '239.0.2.154'
FILE_XML = '/tmp/tv_grab_es_movistar.xml'
FILE_M3U = '/tmp/tv_grab_es_movistar'
FILE_LOG = '/tmp/tv_grab_es_movistar.log'


# Andalucia 15
# Aragon    34
# Asturias  13
# Cantabria 29
# Castilla# la# Mancha  38
# Castilla# y# Leon 4
# Cataluna  1
# Comunidad# Valenciana 6
# Extremadura   32
# Galicia   24
# Islas# Baleares   10
# Islas# Canarias   37
# La# Rioja 31
# Madrid    19
# Murcia    12
# Navarra   35
# Pais# Vasco   36
PROVINCE = '19'
ENCODING_EPG = 'utf-8'
DECODING_EPG = 'latin1'
ENCODING_SYS = sys.getdefaultencoding()
#print "The default system encoding is : " + ENCODING_SYS
sys.setdefaultencoding(ENCODING_EPG)
#ENCODING_SYS = sys.getdefaultencoding()
#print "The system encoding has been set to : " + ENCODING_SYS


if len(sys.argv) > 1:
#    if str(sys.argv[1]) == "--description" or  str(sys.argv[1]) == "-d":
    day = sys.argv[1]
    FILE_XML = '/tmp/tv_grab_es_movistar_'+str(day)+'.xml'
    print "Spain (Multicast Movistar - py)"
else:
    print "Usage: "+ sys.argv[0]+' [DAY NUMBER(0 today)]'
    exit()


# Example, for debugging purpose only
programmes = [{'audio': {'stereo': u'stereo'},
                   'category': [(u'Biz', u''), (u'Fin', u'')],
                   'channel': u'C23robtv.zap2it.com',
                   'date': u'2003',
                   'start': u'20030702000000 ADT',
                   'stop': u'20030702003000 ADT',
                   'title': [(u'This Week in Business', u'')]},
                  {'audio': {'stereo': u'stereo'},
                   'category': [(u'Comedy', u'')],
                   'channel': u'C36wuhf.zap2it.com',
                   'country': [(u'USA', u'')],
                   'credits': {'producer': [u'Larry David'], 'actor': [u'Jerry Seinfeld']},
                   'date': u'1995',
                   'desc': [(u'In an effort to grow up, George proposes marriage to former girlfriend Susan.',
                             u'')],
                   'episode-num': (u'7 . 1 . 1/1', u'xmltv_ns'),
                   'language': (u'English', u''),
                   'last-chance': (u'Hah!', u''),
                   'length': {'units': u'minutes', 'length': '22'},
                   'new': True,
                   'orig-language': (u'English', u''),
                   'premiere': (u'Not really. Just testing', u'en'),
                   'previously-shown': {'channel': u'C12whdh.zap2it.com',
                                        'start': u'19950921103000 ADT'},
                   'rating': [{'icon': [{'height': u'64',
                                         'src': u'http://some.ratings/PGicon.png',
                                         'width': u'64'}],
                               'system': u'VCHIP',
                               'value': u'PG'}],
                   'star-rating': {'icon': [{'height': u'32',
                                             'src': u'http://some.star/icon.png',
                                             'width': u'32'}],
                                   'value': u'4/5'},
                   'start': u'20030702000000 ADT',
                   'stop': u'20030702003000 ADT',
                   'sub-title': [(u'The Engagement', u'')],
                   'subtitles': [{'type': u'teletext', 'language': (u'English', u'')}],
                   'title': [(u'Seinfeld', u'')],
                   'url': [(u'http://www.nbc.com/')],
                   'video': {'colour': True, 'aspect': u'4:3', 'present': True,
                             'quality': 'standard'}}]


# Main starts
# TO-DO: Adding 7th day for EPG

#print "Looking for the ip of your province"
#ipprovince = getxmlprovince(MCAST_CHANNELS,MCAST_PORT,PROVINCE)
logger.info("Getting channels list")
now = datetime.datetime.now()
OBJ_XMLTV = ET.Element("tv" , {"date":now.strftime("%Y%m%d%H%M%S"),"source_info_url":"https://go.tv.movistar.es","source_info_name":"Grabber for internal multicast of MovistarTV","generator_info_name":"python-xml-parser","generator_info_url":"http://wiki.xmltv.org/index.php/XMLTVFormat"})
#OBJ_XMLTV = ET.Element("tv" , {"date":now.strftime("%Y%m%d%H%M%S")+" +0200"})

channelsstream = TvaStream(MCAST_CHANNELS,MCAST_PORT)
channelsstream.getfiles()
xmlchannels = channelsstream.files()["2_0"]
xmlchannelspackages = channelsstream.files()["5_0"]

channelparser = TvaParser(xmlchannels)
rawclist = {}
rawclist = channelparser.channellist(rawclist)


channelspackages = {}
channelspackages = TvaParser(xmlchannelspackages).getpackages()

clist = {}
for package in channelspackages.keys():
  clist[package] = {}
  for channel in channelspackages[package].keys():
    clist[package][channel] = rawclist[channel]
    clist[package][channel]["order"] = channelspackages[package][channel]["order"]
    channelsm3u = channelparser.channels2m3u(clist[package])
    if os.path.isfile(FILE_M3U+package+".m3u"):
        os.remove(FILE_M3U+package+".m3u")
    fM3u = open(FILE_M3U+package+".m3u", 'w+')
    fM3u.write(channelsm3u)
    fM3u.close
    


OBJ_XMLTV = channelparser.channels2xmltv(OBJ_XMLTV,rawclist)

i=int(day)+132
logger.info("\nReading day " + str(i - 132) +"\n")
epgstream = TvaStream('239.0.2.'+str(i),MCAST_PORT)
epgstream.getfiles()
for i in epgstream.files().keys():
    logger.info("Parsing "+i)
    epgparser = TvaParser(epgstream.files()[i])
    epgparser.parseepg(OBJ_XMLTV,rawclist)

# A standard grabber should print the xmltv file to the stdout
ElementTree(OBJ_XMLTV).write(FILE_XML)
print "Grabbed "+ str(len(OBJ_XMLTV.findall('channel'))) +" channels and "+str(len(OBJ_XMLTV.findall('programme')))+" programmes"

exit()
