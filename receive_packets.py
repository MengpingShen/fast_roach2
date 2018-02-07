#! /usr/bin/python
import corr,socket,array
#import socket,pylab,matplotlib,math,corr,array
import struct
import time
import numpy as np


if __name__ == '__main__':
       	#fpga=corr.katcp_wrapper.FpgaClient('10.0.1.170')
       	IP1 = "10.10.12.2" #bind on IP addresses
       	IP2 = "10.10.13.3" #bind on IP addresses
       	IP3 = "10.10.14.4" #bind on IP addresses
       	IP4 = "10.10.15.5" #bind on IP addresses
       	#IP = "" #bind on all IP addresses
       	PORT = 12345
	file_name = "fast-test.dat"
       	sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       	sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       	sock3 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       	sock4 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       	sock1.bind((IP1, PORT))
       	sock2.bind((IP2, PORT))
       	sock3.bind((IP3, PORT))
       	sock4.bind((IP4, PORT))
       	if PORT != -1:
               	print "10GbE port connect done!"
       	#data, addr = sock.recvfrom(4096+8)

      	#header = struct.unpack('<Q', data[0:8])[0]
	for i in range(1):
		with open(file_name,'a') as f:
       			data1, addr1 = sock1.recvfrom(4104)
       			data2, addr2 = sock2.recvfrom(4104)
       			data3, addr3 = sock3.recvfrom(4104)
       			data4, addr4 = sock4.recvfrom(4104)
			header1 = struct.unpack('<Q',data1[0:8])[0]
		      	header2 = struct.unpack('<Q', data2[0:8])[0]
		      	header3 = struct.unpack('<Q', data3[0:8])[0]
		      	header4 = struct.unpack('<Q', data4[0:8])[0]
			print 'header of FRB/Pulsar power term is: %x, and the source ID is: %x' % (header1,(header1>>56))
			print 'header of FRB/Pulsar cross term is: %x, and the source ID is: %x' % (header2,(header2>>56))
			print 'header of SETI Pol1 term is: %x, and the source ID is: %x' % (header3,(header3>>56))
			print 'header of SETI Pol2 term is: %x, and the source ID is: %x' % (header4,(header4>>56))
			np.save(f,data1)
			np.save(f,data2)
			np.save(f,data3)
			np.save(f,data4)
		print 'received %d bytes' %len(data1),
		print 'from', addr1
		print 'received %d bytes' %len(data2),
		print 'from', addr2
		print 'received %d bytes' %len(data3),
		print 'from', addr3
		print 'received %d bytes' %len(data4),
		print 'from', addr4
