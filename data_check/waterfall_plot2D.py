#! /usr/bin/python
import corr,socket,array
#import socket,pylab,matplotlib,math,corr,array
import pylab
import matplotlib.pyplot as plt
import struct
import time
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.collections import PolyCollection
from matplotlib import colors as mcolors
from matplotlib.colors import colorConverter
N_TIME = 40
N_FREQ = 4096
N_DROPS = 200*2
T_SAMP = 256e-6 # us
SAMP_RATE = 1024 # MHz
BW = SAMP_RATE / 2.0
Ch_BW = BW / N_FREQ

def cc(arg):
    	return mcolors.to_rgba(arg, alpha=0.9)
if __name__ == '__main__':
	data1_tmp = np.zeros((N_TIME,N_FREQ))
	data2_tmp = np.zeros((N_TIME,N_FREQ))
	xx_tmp1 = np.zeros((N_TIME,N_FREQ/2))
	xx_tmp2 = np.zeros((N_TIME,N_FREQ/2))
	yy_tmp1 = np.zeros((N_TIME,N_FREQ/2))
	yy_tmp2 = np.zeros((N_TIME,N_FREQ/2))
	xx = np.zeros((N_TIME,N_FREQ))
	yy = np.zeros((N_TIME,N_FREQ))
	seq1 = N_TIME*[long(0)]
	seq2 = N_TIME*[long(0)]
       	IP1 = "10.10.12.2" #bind on IP addresses
       	PORT = 12345
	#file_name = "fast-test.dat"
       	sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       	sock1.bind((IP1, PORT))
       	if PORT != -1:
               	print "10GbE port connect done!"

	for i in range(N_TIME):
		for j in range(N_DROPS):
			sock1.recvfrom(4104)
		data1, addr1 = sock1.recvfrom(4104)
		data2, addr2 = sock1.recvfrom(4104)
		header1 = struct.unpack('<Q', data1[0:8])[0]
		header2 = struct.unpack('<Q', data2[0:8])[0]
		data1_tmp[i] = np.fromstring(data1[8:],dtype=np.uint8)
		data2_tmp[i] = np.fromstring(data2[8:],dtype=np.uint8)

	        xx_tmp1[i] = data1_tmp[i][0::2]
	        yy_tmp1[i] = data1_tmp[i][1::2]
	        xx_tmp2[i] = data2_tmp[i][0::2]
	        yy_tmp2[i] = data2_tmp[i][1::2]
		seq1[i] = header1 & 0x00ffffffffffffff
		seq2[i] = header2 & 0x00ffffffffffffff
		print 'seq1 of FRB/Pulsar power term is: %ld, and the source ID is: %x' % (seq1[i],(header1>>56))
                xx[i] = xx_tmp1[i].tolist() + xx_tmp2[i].tolist()
                yy[i] = yy_tmp1[i].tolist() + yy_tmp2[i].tolist()

	for kk in range(0,N_TIME):
                pylab.plot(xx[kk]-kk*200, 'b')
	#fig = plt.figure()
	#ax = fig.gca(projection='3d')
	#cc = lambda arg: colorConverter.to_rgba(arg, alpha=0.6)
	#ax = fig.add_subplot(111, projection='3d')
	#ax = Axes3D(fig)
	#T_tick = np.arange(0,N_DROPS*T_SAMP*N_TIME,N_DROPS*T_SAMP)
#	T_tick = np.arange(N_TIME)
#	F_tick = np.arange(0,BW,Ch_BW)
#	waterfall = []
#	for t in T_tick:
#		waterfall.append(list(zip(F_tick,xx[t])))
#	xmin = np.floor(np.min(F_tick))
#	xmax = np.ceil(np.max(F_tick))
#	ymin = np.floor(np.min(T_tick))
#	ymax = np.ceil(np.max(T_tick))
#	zmin = np.floor(np.min(xx))
#	zmax = np.ceil(np.max(np.abs(xx)))
#	#face_colors = 10*['b','g','r','c']
#	face_colors = 5*[cc('b'), cc('g'), cc('r'), cc('c'), cc('m'), cc('y'), cc('k'), cc('w')]
#	#face_colors = [colorConverter.to_rgba(c) for c in plt.rcParams['axes.prop_cycle'].by_key()['color']]
#	#poly = PolyCollection(waterfall,sizes=(2,), facecolors=face_colors,linewidths = (20,))
#	poly = PolyCollection(waterfall, facecolors=face_colors,linewidths = (10,))
#	#poly.set_alpha(0.7)
#	ax.add_collection3d(poly, zs=T_tick, zdir='y')
#	ax.set_xlabel('Freq')
#	ax.set_ylabel('Time')
#	ax.set_zlabel('Amp')
#  	ax.set_xlim(xmin,xmax)
#  	ax.set_ylim(ymin,ymax)
#  	ax.set_zlim(zmin,zmax)

	#Axes3D.plot_wireframe(T_tick,F_tick,xx)
        pylab.xlabel('Freq Channels')
        pylab.ylabel('Amp')
        plt.show()

#
#		with open(file_name,'a') as f:
#       			data1[i], addr1 = sock1.recvfrom(4104)
#		      	headers = struct.unpack('<Q', data1[0:8])[0]
#			seq1 = headers & 0x00ffffffffffffff
#			#print 'seq of FRB/Pulsar power term is: %x, and the source ID is: %x' % (seq1,(headers>>56))
#			print 'seq of FRB/Pulsar power term is: %ld, and the source ID is: %x' % (seq1,(headers>>56))
#			np.save(f,data1)
#		print 'received %d bytes' %len(data1),
#		print 'from', addr1
