# Stardard tools
import struct
import re
import sys
import os
import itertools
import logging
import json

# Networking
import socket
from errno import EAGAIN

# Time handling
import time
import pytz
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

    def _getchunk(self,socket):
        #Struct of header - first 12 bytes
        # end   xmlsize   type   ?  id        chunk# *10   total chunks     \0
        # --   --------   -----  ------  ----  ---------  -------------      --
        # 00   00 00 00    F1    X 0 00   00     00 00          00           00
        #FIXME: XMLsize print is incorrect
        data = socket.recv(1500)
        chunk = {}
        chunk["end"] = struct.unpack('B',data[:1])[0]
        chunk["size"] = struct.unpack('>HB',data[1:4])[0]
        chunk["filetype"] = struct.unpack('B',data[4:5])[0]
        chunk["fileid"] = struct.unpack('>H',data[5:7])[0]&0x0fff
        chunk["chunk_number"] = struct.unpack('>H',data[8:10])[0]/0x10
        chunk["chunk_total"] = struct.unpack('B',data[10:11])[0]
        chunk["data"] = data[12:]
        self.logger.debug("Chunk "+str(chunk["chunk_number"])+"/"+str(chunk["chunk_total"])+" ---- e:"+str(chunk["end"])+" s:"+        str(chunk["size"])+" f:"+str(chunk["fileid"]))
        return chunk



    def getfiles(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(3)
        sock.bind((self.mcast_grp, self.mcast_port))
        mreq = struct.pack("=4sl", socket.inet_aton(self.mcast_grp), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        loop = True
        chunk = {}
        chunk["end"] = 0
	N = 335
        #Wait for an end chunk to start by the beginning
        while not (chunk["end"]):
            chunk = self._getchunk(sock)
            firstfile = str(chunk["filetype"])+"_"+str(chunk["fileid"])
        #Loop until firstfile
        while (loop):
                xmldata=""
                chunk = self._getchunk(sock)
                #Discard headers
                body=chunk["data"]
                while not (chunk["end"]):
                        xmldata+=body
                        chunk = self._getchunk(sock)
                        body=chunk["data"]
                #Discard last 4bytes binary footer?
                xmldata+=body[:-4]
                self._files[str(chunk["filetype"])+"_"+str(chunk["fileid"])]=xmldata
		N = N - 1
                if (str(chunk["filetype"])+"_"+str(chunk["fileid"]) == firstfile or N == 0):
                    loop = False
        sock.close()

class TvaParser(object):
    ENCODING_EPG = "utf-8"

    def __init__(self,xmldata):
        self.xmldata = xmldata
        self.logger = logging.getLogger('movistarxmltv.tva.TvaParser')

    def get_mcast_demarcationip(self,dem_code):
        regexp = re.compile("DEM_" + str(dem_code) +  "\..*?Address\=\\\"(.*?)\\\".*?",re.DOTALL)
        return regexp.findall(self.xmldata)[0]

    def channellist(self,clist):
        root = ET.fromstring(self.xmldata)
        services = root[0][0].findall("{urn:dvb:ipisdns:2006}SingleService")
        for i in services:
            channelid = i[1].attrib["ServiceName"]
            clist[channelid] = {}
            #clist[channelid]["logo"] = i[1].attrib["logoURI"]
            url = "http://172.26.22.23:2001/appclient/incoming/epg/MAY_1/imSer/"+channelid+".jpg"
            clist[channelid]["logo"] = url
            clist[channelid]["address"] = i[0][0].attrib["Address"]
            clist[channelid]["port"] = i[0][0].attrib["Port"]
            clist[channelid]["name"] = i[2][0].text
            clist[channelid]["shortname"] = i[2][1].text
            clist[channelid]["desc"] = i[2][2].text
            clist[channelid]["tags"] = i[2][3][0].text.split("/")
        return clist

    def getpackages(self):
      root = ET.fromstring(self.xmldata)
      packages = root[0].findall("{urn:dvb:ipisdns:2006}Package")
      packageslist = {}
      for p in packages:
        services =  p.findall("{urn:dvb:ipisdns:2006}Service")
        package = p[0].text
        packageslist[package] = {}
        for s in services:
          channelid = s[0].attrib["ServiceName"]
          packageslist[package][channelid] = {}
          packageslist[package][channelid]["order"] = s[1].text
      return packageslist

    def channels2xmltv(self,xmltv,clist):
        for channelid in clist.keys():
            channelName = clist[channelid]["name"]
            channelId = channelid
            channelKey = clist[channelid]["shortname"]
            channelIp = clist[channelid]["address"]
            channelPort = str(clist[channelid]["port"])
            channelLogo = clist[channelid]["logo"]
            cChannel = SubElement(xmltv,'channel',{"id": channelKey })
            cName = SubElement(cChannel, "display-name", {"lang":"es"})
            cicon = SubElement(cChannel, "icon", {"src": channelLogo })
            cName.text = channelName
        return xmltv

    def channels2m3u(self,clist):
        m3ucontent = "#EXTM3U\n"
        for channelid in sorted(clist, key=lambda key: int(clist[key]["order"])):
            channelName = clist[channelid]["name"]
            channelId = channelid
            channelKey = clist[channelid]["shortname"]
            channelIp = clist[channelid]["address"]
            channelPort = str(clist[channelid]["port"])
            channelTags = clist[channelid]["tags"]
            try:
                channelOrder = clist[channelid]["order"]
            except:
                channelOrder = "99999"
            channelLogo = clist[channelid]["logo"]
            m3ucontent += "#EXTINF:-1," + channelOrder + ' - ' + channelName + '\n'
            m3ucontent += "#EXTTV:"+','.join(channelTags)+";es;"+channelKey+";"+channelLogo+'\n'
            m3ucontent += "rtp://@" + channelIp + ":" + channelPort + '\n'
        return m3ucontent

    def channels2m3usimple(self,clist):
            m3ucontent = "#EXTM3U\n"
            for channelid in sorted(clist, key=lambda key: int(clist[key]["order"])):
                channelName = clist[channelid]["name"]
                channelId = channelid
                channelKey = clist[channelid]["shortname"]
                channelIp = clist[channelid]["address"]
                channelPort = str(clist[channelid]["port"])
                channelTags = clist[channelid]["tags"]
                try:
                    channelOrder = clist[channelid]["order"]
                except:
                    channelOrder = "99999"
                channelLogo = clist[channelid]["logo"]
                m3ucontent += "#EXTINF:-1 tvg-id=\""+channelKey+"\" tvg-logo=\""+channelid+".jpg\", "+ channelName + '\n'
                m3ucontent += "rtp://@" + channelIp + ":" + channelPort + '\n'
                return m3ucontent

    def parseepg(self,xmltv,clist):
        try:
            root = ET.fromstring(self.xmldata)
        except ET.ParseError, v:
            row, column = v.position
            self.logger.error("Error parsing xml, skipping...")
            self.logger.error(str(ET.ParseError))
            self.logger.error("error on row" + str(row) + "column" + str(column) + ":" + str(v))
            return
        #root = tree.getroot()

        if root[0][0][0].get('serviceIDRef') is not None:
            channelid = root[0][0][0].get('serviceIDRef')
        else:
            self.logger.info("No serviceIDRef found")
            return None

        for child in root[0][0][0]:
            programmeId = None
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
                startTimeXml = child[2].text.replace('\n', ' ') # Start time
                startTimePy = datetime.datetime.strptime(startTimeXml,'%Y-%m-%dT%H:%M:%S.%fZ')
                startTime = startTimePy.strftime('%Y%m%d%H%M%S') + ' +0000'

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
                stopTime = stopTimePy.strftime('%Y%m%d%H%M%S') + ' +0000' # Stop time


            try:
                url ='http://www-60.svc.imagenio.telefonica.net:2001/appserver/mvtv.do?action=getEpgInfo&extInfoID='+ programmeId +'&tvWholesaler=1'
                strProgramme = urllib.urlopen(url).read().replace('\n',' ')
                jsonProgramme = json.loads(strProgramme)['resultData']
            except:
                jsonProgramme = {}
                self.logger.error("Download program info failed")

            #   Genre can be also got from the extra information
            #    s = strProgramme[:]
            #    genre = s.split('"genre":"')[1].split('","')[0] # Genre
            year = jsonProgramme.get("productionDate")

            s = strProgramme[:]
            fullTitle = child[1][0].text.replace('\n', ' ').replace('Cine: ', '')

            s = fullTitle[:]
            m = re.search(r"(.*?) T(\d+) Cap. (\d+) - (.+)", s)
            n = re.search(r"(.*?) T(\d+) Cap. (\d+)", s)
            p = re.search(r"(.*?): (.*?)", s)
            title = None
            episodeShort = None
            extra = ""
            if m:
                try:
                    season = int(m.group(2))  # season
                    episode = int(m.group(3)) # episode
                    episodeTitle =  m.group(4)
                    if episode < 10:
                        episode = "0"+str(episode)
                    if season < 10:
                        season = "0"+str(season)
                    episodeShort = "S"+str(season)+"E"+str(episode)
                    extra =  episodeShort +" "+episodeTitle
                except ValueError:
                    self.logger.error("m: Error getting episode in: " + fullTitle)
                title = m.group(1) # title

            elif n:
                try:
                    season = int(n.group(2))  # season
                    episode = int(n.group(3)) # episode
                    if episode < 10:
                        episode = "0"+str(episode)
                    if season < 10:
                        season = "0"+str(season)
                    episodeShort = "S"+str(season)+"E"+str(episode)
                    extra =  episodeShort
                except ValueError:
                    self.logger.error("n: Error getting episode in: " + fullTitle)
                title = n.group(1) # title

            elif s.find(': Episodio ') > 0 :
                try:
                    episode = re.findall(r'[0-9]+', s)[0] # Episode
                    season = 0
                except ValueError:
                    self.logger.error("Error getting episode in: " + fullTitle)
                title = s.split(': Episodio ')[0] # Title
            elif p:
                self.logger.info("Grabbing episode in: " + fullTitle)
                try:
                    title = p.group(1) # title
                    episodeTitle =  p.group(2)
                    episode = None
                    season = None
                except ValueError:
                    self.logger.error("n: Error getting episode in: " + fullTitle)

            else:
                episode = None
                season = None
                title = fullTitle[:]
            title = title.replace('\n',' ').encode(TvaParser.ENCODING_EPG)


            description = jsonProgramme.get("description")
            subgenre = jsonProgramme.get("subgenre")
            originalTitle = jsonProgramme.get("OriginalTitle")
            #if jsonProgramme.get("longTitle") is not None:
            #    title = jsonProgramme.get("longTitle")[0]
            mainActors = jsonProgramme.get("mainActors")

            ############################################################################
            # Creating XMLTV with XML libraries instead XMLTV to avoid encoding issues #
            ############################################################################
            cid = channelid.replace(".imagenio.es","")
            if cid in clist.keys():
                channelKey = clist[cid]["shortname"]
            else:
                channelKey = cid
           # cProgramme = SubElement(OBJ_XMLTV,'programme', {"start":startTime+" +0200", "stop": stopTime+" +0200", "channel": channelKey })
            cProgramme = SubElement(xmltv,'programme', {"start":startTime, "stop": stopTime, "channel": channelKey })
            cTitle = SubElement(cProgramme, "title", {"lang":"es"})
            cTitle.text = title
            category = None

            if subgenre is not None:
                category = subgenre
            elif genre is None:
                category = genre

            if len(extra) > 2:
                extra = extra + " | "

            if category is not None and year is not None and originalTitle is not None:
                extra = extra +  category+" | "+year[0]+" | "+originalTitle
            elif category is not None and year is  None and originalTitle is None:
                extra = extra +  category
            elif category is not None and year is not None and originalTitle is None:
                extra = extra +  category+" | "+year[0]

            if extra is not None:
                cDesc = SubElement(cProgramme, "sub-title", {"lang":"es"})
                cDesc.text = extra

            if description is not None:
                cDesc = SubElement(cProgramme, "desc", {"lang":"es"})
                cDesc.text = description

            cCredits = SubElement(cProgramme, "credits")
            if mainActors is not None:
                for i in mainActors[0].split(","):
                  cActors  = SubElement(cCredits, "actor")
                  cActors.text = i

            if year is not None:
                cDate = SubElement(cProgramme, "date")
                cDate.text = year[0]

            json_data=open(os.path.split(__file__)[0]+"/categories.json").read()
            categories_map = json.loads(json_data)

            if categories_map.get(category) is not None:
                category = categories_map.get(category)

            cCategory = SubElement(cProgramme, "category", {"lang":"es"})

            cCategory.text = category
            if len(duration) > 0:
                cDuration = SubElement(cProgramme, "length", {"units":"minutes"})
                cDuration.text = duration

            if episode is not None and season is not None:
                cEpisode = SubElement(cProgramme, "episode-num", {"system":"xmltv_ns"})
                cEpisode.text = str(int(season) - 1)+"."+str(int(episode) - 1)+"."
            elif episode is not None and season is None:
                cEpisode = SubElement(cProgramme, "episode-num", {"system":"xmltv_ns"})
                cEpisode.text = "."+str(int(episode) - 1)+"."
            elif episode is None and season is not None:
                cEpisode = SubElement(cProgramme, "episode-num", {"system":"xmltv_ns"})
                cEpisode.text = str(int(season) - 1)+".."

            rating_tvchip = {
                    "Suitable for all audiences": "TV-G",
                    "Suitable for audiences 7 and over": "TV-Y7",
                    "Suitable for audiences 12 and over": "TV-14",
                    "Suitable for audiences 18 and over": "TV-MA"}
            if child[1].find('{urn:tva:metadata:2007}ParentalGuidance')[0][0].text is not None:
                rating = rating_tvchip.get(child[1].find('{urn:tva:metadata:2007}ParentalGuidance')[0][0].text.replace('\n',' '))
                cRating = SubElement(cProgramme, "rating", {"system":"VCHIP"})
                cRatingvalue = SubElement(cRating, "value")
                cRatingvalue.text = rating
