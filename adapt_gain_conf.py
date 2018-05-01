############### adaptive gain configuration for FAST Multi-beam backend -- Roach2s  ###########
### This function is used to find a proper gain value for 8 bit output data. Set the gain value step by step to increase or decrease the value of output data. Once the average data falls into the preset range, the entire adaptive adjustment is completed. 
#################

#!/usr/bin/python

import time,struct, socket
from corr import katcp_wrapper, log_handlers
import numpy as np

roach2 = 'r2d021403.s6.pvt' # (10.0.1.169) mounted on asa2
katcp_port = 7147

IP1 = "10.10.12.2" #bind on IP addresses
PORT = 12345

N_FREQ = 4096
thres_low = 10 # low threshold  
thres_high = 20 # high threshold
gain_step = 0x0100 # step gain

if __name__ == '__main__':

        data1_tmp = np.zeros(N_FREQ)
        data2_tmp = np.zeros(N_FREQ)
	unit = 'u0'
	# connect to roach2
       	print('Connecting to server %s on port %i... ' % (roach2, katcp_port)),
       	fpga = katcp_wrapper.FpgaClient(roach2)
       	time.sleep(0.1)

       	if fpga.is_connected():
       	        print('ok')
       	else:
       	        print('ERROR connecting to server %s on port %i.\n' % (roach2,katcp_port))
       	        exit_fail()
	# read the original gain value
	gain = fpga.read_int(unit+'_gain')
	print('original gain from %s is: 0x%X ...') % (unit,gain)

	
	while True:
		# receive data from 10 GbE port, close the socket after packets receiving
		sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        	sock1.bind((IP1, PORT))
		data1, addr1 = sock1.recvfrom(4104)
        	data2, addr2 = sock1.recvfrom(4104)
		sock1.close()
		# extract the xx and yy spectrum from 2 packets
        	header1 = struct.unpack('<Q', data1[0:8])[0]
        	header2 = struct.unpack('<Q', data2[0:8])[0]
        	data1_tmp  = np.fromstring(data1[8:],dtype=np.uint8)
        	data2_tmp  = np.fromstring(data2[8:],dtype=np.uint8)
		xx = np.append(data1_tmp [0::2],data2_tmp [0::2])
		yy = np.append(data1_tmp [1::2],data2_tmp [1::2])
		# calculate the average value of the spectrum
		avg_xx = np.average(xx)
		avg_yy = np.average(yy)
		max_xx = np.amax(xx)
		max_yy = np.amax(yy)
		print 'max. value of xx is: %d, max. value of yy is: %d' % (max_xx,max_yy)
		print 'average value of xx is: %f, average value of yy is: %f' % (avg_xx,avg_yy)

		# if the average data falls into the preset range then quit
		if((avg_xx > thres_low) & (avg_xx < thres_high)):
			print('Adaptive gain configuration for xx is done!')
			# if yy heven't finsh then only adjust yy
			if((avg_yy > thres_low) & (avg_yy < thres_high)):
				print('Adaptive gain configuration for yy is done!')
				print('Adaptive gain configuration is done!')
				break
			elif(avg_yy < thres_low):
				gain += gain_step <<16
			elif(avg_yy > thres_high):
				gain -= gain_step <<16
		elif(avg_xx < thres_low):
			gain += gain_step <<16 | gain_step
		elif(avg_xx > thres_high):
			gain -= gain_step <<16 | gain_step
		
		print('Configuring spectrometer "%s" scale coefficients, gain=0x%X ... ' % (unit, gain)),
		fpga.write_int(unit + '_gain', gain) # in 16_8-16_8 format
		print('done')
		print('waitting to refresh data ...')
		time.sleep(1)
		print('done')
