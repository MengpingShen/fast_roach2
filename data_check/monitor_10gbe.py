#! /usr/bin/python
import corr,socket,array
import socket,math,corr,array
import struct
import time
import matplotlib.pyplot as plt
import numpy as np

N_Chans = 4096
SAMP_RATE = 1024 # MHz
BW = SAMP_RATE / 2.0
Ch_BW = BW / N_Chans

def plot_spectrum():

        data1, addr1 = sock1.recvfrom(4104)
        data2, addr2 = sock1.recvfrom(4104)
        header1 = struct.unpack('<Q',data1[0:8])[0]
        header2 = struct.unpack('<Q',data2[0:8])[0]
        data1_tmp=np.fromstring(data1[8:],dtype=np.uint8)
        data2_tmp=np.fromstring(data2[8:],dtype=np.uint8)
        xx_tmp1 = data1_tmp[0::2]
        yy_tmp1 = data1_tmp[1::2]
        xx_tmp2 = data2_tmp[0::2]
        yy_tmp2 = data2_tmp[1::2]
        seq1 = header1 & 0x00ffffffffffffff
	seq2 = header2 & 0x00ffffffffffffff
	if((seq1%2==0) & (seq2%2==1)):
		xx = xx_tmp1.tolist() + xx_tmp2.tolist()
		yy = yy_tmp1.tolist() + yy_tmp2.tolist()
	elif((seq1%2==1) & (seq2%2==0)):
		xx = xx_tmp2.tolist() + xx_tmp1.tolist()
		yy = yy_tmp2.tolist() + yy_tmp1.tolist()
	else:
		xx = N_Chans*[0]
		yy = N_Chans*[0]
	print "seq is %lu, ID source is %X" % (seq1,header1>>56)
	#print "header1 is %lu, ID source is %X" % (header2,header2>>56)
	#print "seq1 is %lu, seq2 is %lu" % (seq1,seq2)
	freq = np.arange(0,N_Chans*Ch_BW,Ch_BW)
        plt.clf()
        #print paa
        plt.subplot(211)
        #plt.title('SEQ is '+str(seq),bbox=dict(facecolor='red', alpha=0.5))
        #plt.title('SEQ is '+str(seq1))
        plt.title('Spectrum monitor from 10GbE port')
        #plt.title('xx')      
        #plt.plot(np.log10(paa),color="g")
        plt.plot(freq,xx,color="g")
        #plt.xlim(0,freq)
        plt.ylabel('xx')
        plt.ylim(0,256)
        #plt.ylabel('Power(dBm)')

        #print pbb
        plt.subplot(212)
        #plt.title('yy')      
        #plt.plot(np.log10(pbb),color="b")
        plt.plot(freq,yy,color="b")
        #plt.xlim(0,freq)
        plt.ylim(0,256)
        plt.ylabel('yy')
        plt.xlabel('Freq(MHz)')
        #plt.ylabel('Power(dBm)')

	print ('total power of xx and yy are: %f and %f') % (np.average(xx),np.average(yy))
        fig.canvas.draw()
        fig.canvas.manager.window.after(1000,plot_spectrum)
        return True


if __name__ == '__main__':

	xx = 4096*[0]
	yy = 4096*[0]
	xx_tmp1=2048*[0]
	yy_tmp1=2048*[0]
	xx_tmp2=2048*[0]
	yy_tmp2=2048*[0]
       	IP1 = "192.168.16.11" #bind on IP addresses
       	#IP1 = "192.168.1.127" #bind on IP addresses
       	#IP1 = "10.10.12.2" #bind on IP addresses
       	PORT = 12345
	file_name = "fast-test.dat"
       	sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       	sock1.bind((IP1, PORT))
       	if PORT != -1:
               	print "10GbE port connect done!"
                fig = plt.figure()
                fig.canvas.manager.window.after(1000,plot_spectrum)
                plt.show()
	
