#!/usr/bin/env python
# TO DO:
# - Fixing encoding and parsing issues
# - Adding tv_grab standard options
#   --config-file
# - Moving m3u creation to its own option
# - Using a temporary file to save user province, channels and epg days, so we save time in each execution

# Stardard tools
import sys
import os
import re
import logging
import json
import argparse

# Time handling
import time
import datetime
from datetime import timedelta

# XML
import urllib
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, Comment, ElementTree, dump

# ese's tva lib
from tva import TvaStream, TvaParser


parser = argparse.ArgumentParser()
parser.add_argument("--description",
                    help="show 'Spain: Movistar IPTV grabber'",
                    action="store_true")
parser.add_argument("--capabilities",
                    help="show xmltv capabilities",
                    action="store_true")
parser.add_argument("--quiet",
                    help="Suppress all progress information. The grabber shall only print error-messages to stderr.",
                    action="store_true")
parser.add_argument("--output",
                    help="Redirect the xmltv output to the specified file. Otherwise output goes to stdout.",
                    action="store",
                    dest="filename")
# add default="/tmp/tv_grab_es_movistar.xml" above to save to a
# default file
parser.add_argument("--days",
                    action = "store",
                    type = int,
                    dest = "grab_days",
                    help = "Supply data for X days. Grabber may have an upper limit to the number of days that it can return data for. If X is larger than that limit, the grabber shall return no data for the days that it lacks data for, print a warning to stderr, and exit with an error-code. See XmltvErrorCodes. In other words, if too many days are requested, the grabber will return data for as many days as it can. The default number of days is 'as many as possible'",
                    default = 6)
parser.add_argument("--offset",
                    action = "store",
                    type = int,
                    dest = "grab_offset",
                    help = "Start with data for day today plus X days. The default is 0, today; 1 means start from tomorrow, etc. ",
                    default = 0)
#parser.add_argument("--config-file",
#                    action="store",
#                    dest="config_file",
#                    help = "The grabber shall read all configuration data from the specified file.")

args = parser.parse_args()

if args.description:
    print "Spain: Movistar IPTV grabber"
elif args.capabilities:
    print "baseline"
else:
    logger = logging.getLogger('movistarxmltv')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # log to file
    fh = logging.FileHandler('/tmp/movistar.log')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # log to console
    if not args.quiet:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    reload(sys)

    SOCK_TIMEOUT = 3
    FILE_M3U = '/tmp/tv_grab_es_movistar'
    FILE_LOG = '/tmp/tv_grab_es_movistar.log'

    clientprofile = json.loads(urllib.urlopen("http://172.26.22.23:2001/appserver/mvtv.do?action=getClientProfile").read())['resultData']
    platformprofile = json.loads(urllib.urlopen("http://172.26.22.23:2001/appserver/mvtv.do?action=getPlatformProfile").read())['resultData']
    DEMARCATION =  clientprofile["demarcation"]
    TVPACKAGES = clientprofile["tvPackages"].split("|")
    MCAST_GRP_START = platformprofile["dvbConfig"]["dvbEntryPoint"].split(":")[0]
    MCAST_PORT = int(platformprofile["dvbConfig"]["dvbEntryPoint"].split(":")[1])
    logger.info("Init. DEM="+str(DEMARCATION)+" TVPACKS="+str(TVPACKAGES)+" ENTRY_MCAST="+MCAST_GRP_START+":"+str(MCAST_PORT))

    ENCODING_EPG = 'utf-8'
    DECODING_EPG = 'latin1'
    ENCODING_SYS = sys.getdefaultencoding()
    sys.setdefaultencoding(ENCODING_EPG)

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

    demarcationstream = TvaStream(MCAST_GRP_START,MCAST_PORT)
    demarcationstream.getfiles()
    demarcationxml = demarcationstream.files()["1_0"]
    logger.info("Getting channels source for DEM: "+str(DEMARCATION))
    MCAST_CHANNELS = TvaParser(demarcationxml).get_mcast_demarcationip(DEMARCATION)

    logger.info("Getting channels list from: "+MCAST_CHANNELS)
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
    for package in TVPACKAGES:
        for channel in channelspackages[package].keys():
            clist[channel] = rawclist[channel]
            clist[channel]["order"] = channelspackages[package][channel]["order"]
  
    channelsm3u = channelparser.channels2m3u(clist)
    if os.path.isfile(FILE_M3U+"_client.m3u"):
        os.remove(FILE_M3U+"_client.m3u")
    fM3u = open(FILE_M3U+"_client.m3u", 'w+')
    fM3u.write(channelsm3u)
    fM3u.close
    
    OBJ_XMLTV = channelparser.channels2xmltv(OBJ_XMLTV,rawclist)

    last_day = args.grab_offset + args.grab_days
    if last_day > 6:
        last_day = 6
    for d in range(args.grab_offset, last_day):
        i=int(d)+130
        logger.info("\nReading day " + str(i - 130) +"\n")
        epgstream = TvaStream('239.0.2.'+str(i),MCAST_PORT)
        epgstream.getfiles()
        for i in epgstream.files().keys():
            logger.info("Parsing "+i)
            epgparser = TvaParser(epgstream.files()[i])
            epgparser.parseepg(OBJ_XMLTV,rawclist)

    # A standard grabber should print the xmltv file to the stdout or to
    # filename if called with option --output filename
    if args.filename:
        FILE_XML = args.filename
        ElementTree(OBJ_XMLTV).write(FILE_XML,encoding="UTF-8")
    else:
        dump(ElementTree(OBJ_XMLTV))
    # changed to logger to respect --quiet
    logger.info("Grabbed "+ str(len(OBJ_XMLTV.findall('channel'))) +" channels and "+str(len(OBJ_XMLTV.findall('programme')))+" programmes")

exit()
