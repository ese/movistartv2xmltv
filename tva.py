# Stardard tools
import struct
import re
import sys
import os
import itertools
import logging

# Networking
import socket
from errno import EAGAIN

# Time handling
import time
import datetime
from datetime import timedelta

# XML
import urllib
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, Comment, ElementTree
import pprint
import binascii
from pprint import pprint



module_logger = logging.getLogger('movistarxmltv.tva')


class TvaStream(object):
    def __init__(self,mcast_grp,mcast_port):
        self.mcast_grp = mcast_grp
        self.mcast_port = mcast_port
        self._files = {}
        self.logger = logging.getLogger('movistarxmltv.tva.TvaStream')

    def files(self):
        return self._files

    def getfiles(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(3)
        sock.bind(('', self.mcast_port))
        mreq = struct.pack("=4sl", socket.inet_aton(self.mcast_grp), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        end = 0
        loop = True

        #Wait for an end chunk to start by the beginning
        while not (end):
            data = sock.recv(1500)
            end = struct.unpack('B',data[:1])[0]
            filetype = struct.unpack('B',data[4:5])[0]
            fileid = struct.unpack('>H',data[5:7])[0]&0x0fff
            firstfile = str(filetype)+"_"+str(fileid)

        #Loop until firstfile
        while (loop):
                xmldata=""
                data = sock.recv(1500)

                #Struct of header - first 12 bytes
                # end   xmlsize   type   ?  id        chunk# *10   total chunks     \0
                # --   --------   -----  ------  ----  ---------  -------------      --
                # 00   00 00 00    F1    X 0 00   00     00 00          00           00
                #FIXME: XMLsize print is incorrect
                end = struct.unpack('B',data[:1])[0]
                size = struct.unpack('>HB',data[1:4])[0]
                filetype = struct.unpack('B',data[4:5])[0]
                fileid = struct.unpack('>H',data[5:7])[0]&0x0fff
                chunk_number = struct.unpack('>H',data[8:10])[0]/0x10
                chunk_total = struct.unpack('B',data[10:11])[0]

                #Discard headers
                body=data[12:]
                while not (end):
                        self.logger.debug("Chunk "+str(chunk_number)+"/"+str(chunk_total)+" ---- e:"+str(end)+" s:"+str(size)+" f:"+str(fileid))
                        xmldata+=body
                        data = sock.recv(1500)
                        end = struct.unpack('B',data[:1])[0]
                        size = struct.unpack('>HB',data[1:4])[0]
                        fileid = struct.unpack('>H',data[5:7])[0]&0x0fff
                        filetype = struct.unpack('B',data[4:5])[0]
                        chunk_number = struct.unpack('>H',data[8:10])[0]/0x10
                        chunk_total = struct.unpack('B',data[10:11])[0]
                        body=data[12:]
                self.logger.debug("Chunk "+str(chunk_number)+"/"+str(chunk_total)+" ---- e:"+str(end)+" s:"+str(size)+" f:"+str(fileid))
                #Discard last 4bytes binary footer?
                xmldata+=body[:-4]
                self._files[str(filetype)+"_"+str(fileid)]=xmldata
                if (str(filetype)+"_"+str(fileid) == firstfile):
                    loop = False
        sock.close()

class TvaParser(object):
    ENCODING_EPG = "utf-8"

    def __init__(self,xmldata):
        self.xmldata = xmldata
        self.logger = logging.getLogger('movistarxmltv.tva.TvaParser')

    def channellist(self):
        beginning=0
        end=0
        lista=[]
        now = datetime.datetime.now()

        while (end == 0):
            regexp = re.compile("Port\=\\\"(.*?)\\\".*?Address\=\\\"(.*?)\\\" \/\>.*?imSer\/(.*?)\.jpg.*?Language\=\\\"ENG\\\"\>(.*?)\<\/Name\>",      re.       DOTALL)
            m = regexp.findall(self.xmldata)
            if m:
                lista.append(m)

            if(re.findall("\<BroadcastDiscovery", self.xmldata)):
                beginning=1

            if(beginning==1):
                if(re.findall("\<\/BroadcastDiscovery",self.xmldata)):
                    end=1
                    lista = list(itertools.chain(*lista))
                    lista.sort()
                    return lista

    def channels2xmltv(self,xmltv):
        lista = self.channellist()
        for i in range(0,len(lista)-1):
            channelName = lista[i][3]
            channelId = lista[i][2]
            channelKey = channelName.replace(" ","").encode(TvaParser.ENCODING_EPG)
            channelIp = lista[i][1]
            channelPort = str(lista[i][0])
            cChannel = SubElement(xmltv,'channel',{"id": channelName })
            cName = SubElement(cChannel, "display-name", {"lang":"es"})
            cName.text = channelKey
        return xmltv

    def channels2m3u(self):
        lista = self.channellist()
        m3ucontent = "#EXTM3U\n"
        for i in range(0,len(lista)-1):
            channelName = lista[i][3]
            channelId = lista[i][2]
            channelKey = channelName.replace(" ","").encode(TvaParser.ENCODING_EPG)
            channelIp = lista[i][1]
            channelPort = str(lista[i][0])
            #print "Grabbing " + lista[i][3]
            # M3U file
            m3ucontent += "#EXTINF:-1," + channelName + ' [' + channelId + ']\n'
            m3ucontent += "rtp://@" + channelIp + ":" + channelPort + '\n'
        return m3ucontent

    def getchannelsdic(self):
        lista = self.channellist()
        channels = {}
        for i in range(0,len(lista)-1):
             channelName = lista[i][3]
             channelId = lista[i][2]
             channelKey = channelName.replace(" ","").encode(TvaParser.ENCODING_EPG)
             channelIp = lista[i][1]
             channelPort = str(lista[i][0])
             channels[channelId] = channelKey
        return channels

    def parseepg(self,xmltv,channels):
        try:
            root = ET.fromstring(self.xmldata)
        except ET.ParseError, v:
            row, column = v.position
            self.logger.info("\nError when opening /tmp/programme.xml, skipping...\n")
            self.logger.info(str(ET.ParseError))
            self.logger.info("\nerror on row" + str(row) + "column" + str(column) + ":" + str(v) + "\n")
        #root = tree.getroot()

        if root[0][0][0].get('serviceIDRef') is not None:
            channelid = root[0][0][0].get('serviceIDRef')

        for child in root[0][0][0]:
            if child[0].get('crid') is not None:
                programmeId = child[0].get('crid').split('/')[5]   # id for description
            if child[1][1][0] is not None:
                genre =  child[1][1][0].text #.encode(ENCODING_EPG).replace('\n', ' ') # Genre
            else:
                year = None
            #   20030702000000 XMLTV format
            #   YYYYMMddHHmmss
            #   2014-09-21T22:24:00.000Z IPTV multicast format
            #   YYYY-MM-ddTHH:mm:ss.000Z
            # start and stop are mandatory, so we set a future date so we can at least find the programme
            startTimePy = datetime.datetime.now() + timedelta(weeks=10)
            stopTimePy = startTimePy + timedelta(minutes=1)

            if child[2].text is not None:
                startTimeXml = child[2].text.replace('\n', ' ').split(".")[0].replace('T', ' ') # Start time
                startTimePy = datetime.datetime.strptime(startTimeXml,'%Y-%m-%d %H:%M:%S')
                startTime = startTimePy.strftime('%Y%m%d%H%M%S')

            durationXml = child[3].text.replace('\n', ' ').replace('PT','') # Duration
            if durationXml.find('H') > 0 and durationXml.find('M') > 0:
                durationPy = datetime.datetime.strptime(durationXml,'%HH%MM')
            elif durationXml.find('H') > 0 and durationXml.find('M') < 0:
                durationPy = datetime.datetime.strptime(durationXml,'%HH')
            elif durationXml.find('H') < 0 and durationXml.find('M') > 0:
                durationPy = datetime.datetime.strptime(durationXml,'%MM')
            else:
                durationPy = None
            if durationPy is not None:
                durationPy = 60 * int(durationPy.strftime('%H')) + int(durationPy.strftime('%M'))
                duration = str(durationPy)
                stopTimePy = startTimePy + timedelta(minutes=durationPy)
                stopTime = stopTimePy.strftime('%Y%m%d%H%M%S') # Stop time

            url ='http://www-60.svc.imagenio.telefonica.net:2001/appserver/mvtv.do?action=getEpgInfo&extInfoID='+ programmeId +                '&tvWholesaler=1'
            strProgramme = urllib.urlopen(url).read().replace('\n',' ')
            #   Genre can be also got from the extra information
            #    s = strProgramme[:]
            #    genre = s.split('"genre":"')[1].split('","')[0] # Genre
            s = strProgramme[:]
            if s.find("productionDate")>0:
                year = s.split('"productionDate":["')[1].split('"],"')[0] # Year
            else:
                year = None

            s = strProgramme[:]
            fullTitle = child[1][0].text

            s = fullTitle[:].replace('\n',' ')
            m = re.search(r"(.*?) T(\d+) Cap. (\d+) - (.+)", s)
            n = re.search(r"(.*?) T(\d+) Cap. (\d+)", s)
            title = None
            episodeShort = None
            extra = ""
            if m:
                season = int(m.group(2)) + 1 # season
                episode = int(m.group(3)) +1 # episode
                episodeTitle =  m.group(4)
                if episode < 10:
                    episode = "0"+str(episode)
                if season < 10:
                    season = "0"+str(season)
                episodeShort = "S"+str(season)+"E"+str(episode)
                title = m.group(1) # title
                extra =  episodeShort +" "+episodeTitle
            elif n:
                season = int(n.group(2)) + 1 # season
                episode = int(n.group(3)) +1 # episode
                if episode < 10:
                    episode = "0"+str(episode)
                if season < 10:
                    season = "0"+str(season)
                episodeShort = "S"+str(season)+"E"+str(episode)
                title = n.group(1) # title
                extra =  episodeShort
            elif s.find(': Episodio ') > 0 :
                episode = int(s.split(': Episodio ')[1].split('"')[0]) + 1 # Episode
                season = 0
                title = s.split(': Episodio ')[0] # Title
            else:
                episode = None
                season = None
                title = fullTitle[:]
            title = title.replace('\n',' ').encode(TvaParser.ENCODING_EPG)

            s = strProgramme[:]
            if s.find('"description":"')>0:
                description = s.split('"description":"')[1].split('","')[0] #.decode(DECODING_EPG,'xmlcharrefreplace').encode(ENCODING_EPG,    'xmlcharrefreplace') # Description
            else:
                description = None

            s = strProgramme[:]
            if s.find('"subgenre":"')>0:
                subgenre =  s.split('"subgenre":"')[1].split('","')[0] #.encode(ENCODING_EPG) # Subgenre
            else:
                subgenre = None

            originalTitle = None
 #           s = strProgramme[:]
 #           if s.find('"originalLongTitle":["')>0:
 #               originalTitle =  s.split('"originalLongTitle":"["')[1].split('"')[0]
 #           else:
 #               originalTitle = None



            ############################################################################
            # Creating XMLTV with XML libraries instead XMLTV to avoid encoding issues #
            ############################################################################
            channelShort = channelid.replace(".imagenio.es","")
            if channelShort in channels.keys():
                channelKey = channels[channelShort]
            else:
                channelKey = channelid
           # cProgramme = SubElement(OBJ_XMLTV,'programme', {"start":startTime+" +0200", "stop": stopTime+" +0200", "channel": channelKey })
            cProgramme = SubElement(xmltv,'programme', {"start":startTime, "stop": stopTime, "channel": channelKey })
            cTitle = SubElement(cProgramme, "title", {"lang":"es"})
            cTitle.text = title.encode(TvaParser.ENCODING_EPG)
            cCategory = SubElement(cProgramme, "category", {"lang":"es"})
            category = None
            if subgenre is not None:
                category = subgenre
                cCategory.text = category
            elif genre is None:
                category = genre
                cCategory.text = category

            if episode is not None and season is not None:
                cEpisode = SubElement(cProgramme, "episode-num", {"system":"xmltv_ns"})
                cEpisode.text = str(season)+"."+str(episode)+"."
            elif episode is not None and season is None:
                cEpisode = SubElement(cProgramme, "episode-num", {"system":"xmltv_ns"})
                cEpisode.text = "."+str(episode)+"."
            elif episode is None and season is not None:
                cEpisode = SubElement(cProgramme, "episode-num", {"system":"xmltv_ns"})
                cEpisode.text = str(season)+".."

            if len(duration) > 0:
                cDuration = SubElement(cProgramme, "length", {"units":"minutes"})
                cDuration.text = duration.encode(TvaParser.ENCODING_EPG)
            if year is not None:
                cDate = SubElement(cProgramme, "date")
                cDate.text = year

            if len(extra) > 2:
                extra = extra + " | "

            if category is not None and year is not None and originalTitle is not None:
                extra = extra +  category.encode(TvaParser.ENCODING_EPG)+" | "+year+" | "+originalTitle
            elif category is not None and year is  None and originalTitle is None:
                extra = extra +  category.encode(TvaParser.ENCODING_EPG)
            elif category is not None and year is not None and originalTitle is None:
                extra = extra +  category.encode(TvaParser.ENCODING_EPG)+" | "+year

            if extra is not None:
                cDesc = SubElement(cProgramme, "sub-title", {"lang":"es"})
                cDesc.text = extra


            if description is not None:
                cDesc = SubElement(cProgramme, "desc", {"lang":"es"})
                cDesc.text = description.encode(TvaParser.ENCODING_EPG)
