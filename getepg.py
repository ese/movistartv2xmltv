#!/usr/bin/env python

import socket
import struct
import re
import pprint
import sys
import binascii
import datetime
import itertools


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
	sys.exit(1)

provincia=sys.argv[1]

###################################################
MCAST_GRP = '239.0.2.129'
###################################################

MCAST_PORT = 3937
principio=0
final=0
ipprovincia=0

#print "Buscando IP del servidor Multicast de MovistarTV..."
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(3)
sock.bind(('', MCAST_PORT))
mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)

sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

while True:	
	d = sock.recv(80960000)
	regexp = re.compile("DEM_" + str(provincia) +  "\..*?Address\=\\\"(.*?)\\\".*?",re.DOTALL)
	m = regexp.findall(d)

	if(re.findall("\<\?xml", d)):
		principio=1
	if(principio==1):
		if(re.findall("</ServiceDiscovery>",d)):
			final=1		
		if(final==1):
			if m:
				print m[0]
				ipprovincia = m[0]
				print "IP Encontrada!"
				break
				
			#print "final"
			
principio=0
final=0

#A PARTIR DE AQUI MEJOR NO TOQUES NADA SI NO SABES

###################################################
MCAST_GRP = ipprovincia
###################################################

MCAST_PORT = 3937

#print "Obteniendo datos del servidor Multicast de MovistarTV..."
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(3)
sock.bind(('', MCAST_PORT))
mreq = struct.pack("=4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)

sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)


lista=[]

while True:
	
	data = sock.recv(1500)
	start = data.find("<?xml")
	print start
	if(start>0):
		print data[start:],
		while True:
			data = sock.recv(1500)
			start = data.find("</ServiceDiscovery>")
			if(start>0):
				print data[:start+19],
				exit()
			else:
				print data[13:],
