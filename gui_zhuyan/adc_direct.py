#!/usr/bin/env python

from __future__ import print_function
import sys
import logging, time, struct, socket
import katcp_wrapper, log_handlers


#bitstream = 'adc5g_direct_2016_Mar_31_1627.bof.gz'
#bitstream = 'adc5g_direct_2016_Apr_08_1640.bof.gz'
#bitstream = 'adc5g_direct_2016_Apr_15_1524.bof.gz'
bitstream = 'adc5g_direct_slot1_2016_Sep_05_1623.bof.gz'

roach = 'r1510'
katcp_port = 7147

mac_base = (2<<40) + (2<<32)

fabric_ip = []
fabric_port = []
dest_ip = []
dest_port = []
xgbe_name = []
xgbe_dev = []
dest_ip_regname = []
dest_port_regname = []

for i in range(4):
	fabric_ip_string = '10.0.%d.227' % (i+1);
	fabric_ip.append(struct.unpack('!L',socket.inet_aton(fabric_ip_string))[0])  # convert ip to long
	fabric_port.append(33333)
	dest_ip_string = '10.0.%d.127' % (i+1);
	dest_ip.append(struct.unpack('!L',socket.inet_aton(dest_ip_string))[0])  # convert ip to long
	dest_port.append(12345)
	xgbe_name.append('xgbe%d_core' % i)
	xgbe_dev.append('xgbe%d' % i)
	dest_ip_regname.append('xgbe%d_dest_ip' % i)
	dest_port_regname.append('xgbe%d_dest_port' % i)
	#print(fabric_ip[i], fabric_port[i], dest_ip[i], dest_port[i], xgbe_name[i], xgbe_dev[i], dest_ip_regname[i], dest_port_regname[i])



def exit_fail():
	# print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
	print('FAILURE DETECTED.\n')
	try:
		fpga.stop()
	except: pass
	raise
#	exit()


def exit_clean():
	try:
		fpga.stop()
	except: pass
#	exit()


def pulse_reg(regname):
	try:
		fpga.write_int(regname, 0)
		fpga.write_int(regname, 1)
	except:
		exit_fail()


#START OF MAIN:

if __name__ == '__main__':

	try:
		loggers = []
		lh = log_handlers.DebugLogHandler()
		logger = logging.getLogger(roach)
		logger.addHandler(lh)
		logger.setLevel(10)

		print('Connecting to server %s on port %i ... ' % (roach,katcp_port), end='')
		sys.stdout.flush()
		fpga = katcp_wrapper.FpgaClient(roach, katcp_port, timeout=10,logger=logger)
		time.sleep(1)

		if fpga.is_connected():
			print('ok')
		else:
			print('ERROR connecting to server %s on port %i.\n' % (roach,katcp_port))
			exit_fail()

		print('------------------------')
		print('Programming FPGA with  %s ... ' % bitstream, end='');
		fpga.progdev(bitstream)
		print('done')

		for i in range(4):
			print('Configuring xgbe%d destination IP and port %s:%i ... ' \
				% (i, socket.inet_ntoa(struct.pack('!L', dest_ip[i])), dest_port[i]), end='')
			fpga.write_int(dest_ip_regname[i], dest_ip[i])
			fpga.write_int(dest_port_regname[i], dest_port[i])
			print('done')

		print('Initialize 10GbE ... ', end = '')
		for i in range(4):
			fpga.tap_start(xgbe_dev[i], xgbe_name[i], mac_base + fabric_ip[i], fabric_ip[i], fabric_port[i])
		print('done')

		print("xgbe status: " + bin(fpga.read_uint('status')))

		# This step is very important, otherwise, the packet will offset by 8 bytes.
		# Now this is issued by overflow_guard block
		#print('Reset 10GbE block ... ', end='')
		#pulse_reg('ethrst')
		#print('done')

		# ppsarm block has changed. reset signal not require ARM register to be set any more.
		#print('Issue ARM ... ', end='')
		#pulse_reg('ARM')
		#print('done')

		time.sleep(1)

		print('Reset system ... ', end='')
		pulse_reg('reset')
		print('done')

		while True:
			print("\rxgbe status: " + bin(fpga.read_uint('status')), end='')
			sys.stdout.flush()
			time.sleep(1)

	except KeyboardInterrupt:
		exit_clean()
	except Exception, e:
		print(e)
		exit_fail()

	exit_clean()
