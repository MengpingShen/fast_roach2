#! /usr/bin/python
import corr,socket,array
import pylab
import matplotlib.pyplot as plt
import struct
import time
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.collections import PolyCollection
from matplotlib import colors as mcolors
from matplotlib.colors import colorConverter

N_TIME = 32 # how many spectrums will be shown on the plots
N_FREQ = 4096 # number of frequency channels
N_DROPS = 200*2 # number of dropped packets
T_SAMP = 256 # us
SAMP_RATE = 1024 # MHz
BW = SAMP_RATE / 2.0
Ch_BW = BW / N_FREQ

def cc(arg):
    	return mcolors.to_rgba(arg, alpha=0.9)

if __name__ == '__main__':
	# define 2 dimension array
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
	# binding 10GbE port
       	sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       	sock1.bind((IP1, PORT))
       	if PORT != -1:
               	print "10GbE port connect done!"
	# receive packets from 10GbE Nic and extract two pols spectrum data
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
	# 3D plot initialization
	fig = plt.figure()
	ax = fig.gca(projection='3d')
	T_tick = np.arange(0,N_TIME*N_DROPS*T_SAMP,N_DROPS*T_SAMP)
	#T_tick = np.arange(N_TIME)
	F_tick = np.arange(0,BW,Ch_BW)
	# format data
	waterfall = []
	for t in T_tick:
		waterfall.append(list(zip(F_tick,xx[t/(N_DROPS*T_SAMP)])))
	# set the axis range
	xmin = np.floor(np.min(F_tick))
	xmax = np.ceil(np.max(F_tick))
	ymin = np.floor(np.min(T_tick))
	ymax = np.ceil(np.max(T_tick))
	zmin = np.floor(np.min(xx))
	zmax = np.ceil(np.max(np.abs(xx)))
	# set face color
	face_colors = N_TIME/8*[cc('b'), cc('g'), cc('r'), cc('c'), cc('m'), cc('y'), cc('k'), cc('w')]
	poly = PolyCollection(waterfall, facecolors=face_colors,linewidths = 20)
	ax.add_collection3d(poly, zs=T_tick, zdir='y')
	ax.set_xlabel('Freq(MHz)')
	ax.set_ylabel('Time(us)')
	ax.set_zlabel('Amp')
  	ax.set_xlim(xmin,xmax)
  	ax.set_ylim(ymin,ymax)
  	ax.set_zlim(zmin,zmax)
        plt.show()
