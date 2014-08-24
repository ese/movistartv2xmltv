#!/usr/bin/env python

import socket
import struct
import re
import sys
import os
#import pprint
#import binascii
#import datetime
#import itertools

import xml.etree.ElementTree as ET


MCAST_GRP_START = '239.0.2.129'
MCAST_PORT = 3937

def getrawstream(MCAST_GRP,MCAST_PORT,packets):
	xmldata=""
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.settimeout(3)
	sock.bind(('', MCAST_PORT))
	mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
	sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
	while (packets>0):
		data = sock.recv(1500)
		xmldata+=data
		packets-=1
	return xmldata

def getxmlsepg(MCAST_GRP,MCAST_PORT,files):
        try:
                os.stat(MCAST_GRP)
        except:
                os.mkdir(MCAST_GRP)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(3)
        sock.bind(('', MCAST_PORT))
        mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        end = 0

        #Esperamos al final de una secuencia para comenzar por el principio de un fichero
        while not (end):
            data = sock.recv(1500)
            end = struct.unpack('B',data[:1])[0]
            fileid = struct.unpack('>H',data[5:7])[0]&0x0fff
            #Guardamos el id del fichero para reconocer el final del bucle
            lastfile = fileid

        #Bucle por el numero de ficheros indicado o hasta entrar en loop
        while (files>0):
                xmldata=""
                data = sock.recv(1500)

                #Estructura de cabeceras 12 primeros bytes
                # end   xmlsize     ???   ?  id         #Part*10   Partes totales     \0
                # --   --------   -----  ------  ----  ---------  -------------      --
                # 00   00 00 00    F1    X 0 00   00     00 00          00           00
                #FIXME: XMLsize print is incorrect
                end = struct.unpack('B',data[:1])[0]
                size = struct.unpack('>HB',data[1:4])[0]
                fileid = struct.unpack('>H',data[5:7])[0]&0x0fff
                chunk_number = struct.unpack('>H',data[8:10])[0]/0x10
                chunk_total = struct.unpack('B',data[10:11])[0]

                #Omitimos las cabeceras binarias del fichero xml
                body=data[12:]
                # Si no es la ultima parte del fichero vamos concatenando
                while not (end):
                        print("Chunk "+str(chunk_number)+"/"+str(chunk_total)+" ---- e:"+str(end)+" s:"+str(size)+" f:"+str(fileid))
                        xmldata+=body
                        data = sock.recv(1500)
                        end = struct.unpack('B',data[:1])[0]
                        size = struct.unpack('>HB',data[1:4])[0]
                        fileid = struct.unpack('>H',data[5:7])[0]&0x0fff
                        chunk_number = struct.unpack('>H',data[8:10])[0]/0x10
                        chunk_total = struct.unpack('B',data[10:11])[0]
                        body=data[12:]
                print("Chunk "+str(chunk_number)+"/"+str(chunk_total)+" ---- e:"+str(end)+" s:"+str(size)+" f:"+str(fileid))
                #Omitimos los 4 ultimos bytes que quedan fuera del xml
                xmldata+=body[:-4]
                file = open(MCAST_GRP+"/"+str(fileid)+".xml", "w")
                file.write(xmldata)
                file.close()
                print("File written")
                # Si el fileid es el mismo que detectamos al principio acabamos con el bucle.
                if (fileid == lastfile):
                    files = 1
                files-=1
        sock.close()

def getxmlfile(MCAST_GRP,MCAST_PORT,DISCNAME,ENDSTRING):
	# DISCNAME = xml tag that identifies the file
	# If DISCNAME="" then gets the first file
	# ENDSTRIG= string that ends a file
	xmldata=""
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.settimeout(3)
	sock.bind(('', MCAST_PORT))
	mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
	sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
	while True:
		data = sock.recv(1500)
		start = data.find("<?xml")
		if(start!=-1):
			if(DISCNAME==""):
				isourservice=0
			else:
				isourservice=data.find(DISCNAME)
			if(isourservice!=-1):
				xmldata+=data[start:]
				#print data[start:],
				while True:
					data = sock.recv(1500)
					start = data.find(ENDSTRING)
					if(start!=-1):
						xmldata+=data[12:start+len(ENDSTRING)]
						#print data[13:start+19],
						return(xmldata)
					else:
						xmldata+=data[12:]
					#print data[13:],


def parsechannelxml(xmldata):
	clist=[]
	root = ET.fromstring(xmldata)
	for channel in root.findall('.//{urn:dvb:ipisdns:2006}SingleService'):
		mcaddr=channel.find('.//{urn:dvb:ipisdns:2006}IPMulticastAddress')
		port=mcaddr.get('Port')
		ip=mcaddr.get('Address')
		shortname=channel.find('.//{urn:dvb:ipisdns:2006}ShortName').text
		name=channel.find('.//{urn:dvb:ipisdns:2006}Name').text
		#genre=channel.find('.//{urn:dvb:ipisdns:2006}urn:Name').text
		genre=""
		textualid=channel.find('.//{urn:dvb:ipisdns:2006}TextualIdentifier')
		servicename=textualid.get('ServiceName')
		logouri=textualid.get('logoURI')
		serviceinfo=channel.find('.//{urn:dvb:ipisdns:2006}SI').get('ServiceInfo')
		clist.append({'name':name,'shortname':shortname,'ip':ip,'port':port,'genre':genre,'servicename':servicename,'logouri':logouri,'serviceinfo':serviceinfo})
	return clist

def parseepgservicesxml(xmldata):
	slist=[]
	root = ET.fromstring(xmldata)
	bcg=root.find(".//{urn:dvb:ipisdns:2006}BCG[@Id='EPG']")
	for service in bcg.findall('.//{urn:dvb:ipisdns:2006}DVBSTP'):
		ip=service.get('Address')
		port=service.get('Port')
		source=service.get('Source')
		slist.append({'source':source,'ip':ip,'port':port})
	return slist

if len(sys.argv) < 2:
	print "USO: imagenio.py TUPROVINCIA"
	print "Donde tu provincia es el numero que corresponda de los siguientes:"
	print "24. Galicia"
	print "19. Madrid"
	print "1. Cataluna"
	print "15. Andalucia"
	print "34. Aragon"
	print "13. Asturias"
	print "29. Cantabria"
	print "38. Castilla la Mancha"
	print "4. Castilla y Leon"
	print "6. Comunidad Valenciana"
	print "32. Extremadura"
	print "10. Islas Baleares"
	print "37. Islas Canarias"
	print "31. La Rioja"
	print "12. Murcia"
	print "35. Navarra"
	print "36. Pais Vasco"
#	sys.exit(1)

#provincia=sys.argv[1]

# conseguir la ip de servicio de la provincia
#xmlfile=getxmlfile(MCAST_GRP_START,MCAST_PORT,'ServiceProviderDiscovery',"</ServiceDiscovery>")
#regexp = re.compile("DEM_" + str(provincia) +  "\..*?Address\=\\\"(.*?)\\\".*?",re.DOTALL)
#ipprovincia = regexp.findall(xmlfile)[0]

# conseguir la lista de canales
#xmlfile=getxmlfile(ipprovincia,MCAST_PORT,'BroadcastDiscovery','</ServiceDiscovery>')
#clist=parsechannelxml(xmlfile)
#print clist

# coseguir la lista servicos que sirven la EPG
#xmlfile=getxmlfile(ipprovincia,MCAST_PORT,'BCGDiscovery','</ServiceDiscovery>')
#slist=parseepgservicesxml(xmlfile)
#print slist

#Bajar EPG WIP
for i in range(130,138):
    getxmlsepg('239.0.2.'+str(i),MCAST_PORT,200)

exit()
