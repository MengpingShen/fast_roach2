#!/usr/bin/env python

import katcp_wrapper
import time, struct, socket


#bitstream = 'pkt_p2s_2015_May_08_1620.bof.gz'
bitstream = 'pkt_32_to_8_2017_Nov_08_1625.bof.gz'

roach = 'r1511'
katcp_port = 7147

mac_base = (2<<40) + (2<<32)
fabric_ip_string = '10.32.127.88'
fabric_ip = struct.unpack('!L',socket.inet_aton(fabric_ip_string))[0]  # convert ip to long
fabric_port = 12345

dest_ip_string = '10.32.127.11'
dest_ip = struct.unpack('!L',socket.inet_aton(dest_ip_string))[0]
dest_port = 55555


def exit_fail():
	# print('FAILURE DETECTED. Log entries:\n',lh.printMessages())
	print('FAILURE DETECTED.\n')
	try:
		fpga.stop()
	except: pass
	raise
	#exit()


def exit_clean():
	try:
		fpga.stop()
	except: pass
	#exit()


#START OF MAIN:

if __name__ == '__main__':

	try:
		print('Connecting to server %s on port %i... ' % (roach,katcp_port)),
		fpga = katcp_wrapper.FpgaClient(roach, katcp_port, timeout=10)
		time.sleep(1)

		if fpga.is_connected():
			print('ok\n')
		else:
			print('ERROR connecting to server %s on port %i.\n' % (roach,katcp_port))
			exit_fail()

		print('------------------------')
		print('Programming FPGA with  %s ... ' %bitstream),
		fpga.progdev(bitstream)
		print('done')

		#print(fpga.listdev())

		print('Configuring destination IP and port %s:%i ... '%(socket.inet_ntoa(struct.pack('!L', dest_ip)),dest_port)),
		fpga.write_int('destip', dest_ip)
		fpga.write_int('destport', dest_port)
		print('done')

		divider = 254
		print('Setting divider to %d ...' % divider),
		fpga.write_int('divider', divider)
		print('done')

		print('Initialize 1GbE ... '),
		fpga.tap_start('gbe', 'one_GbE', mac_base + fabric_ip, fabric_ip, fabric_port)
		print('done')

		print('Reset system...'),
		fpga.write_int('reset', 0)
		fpga.write_int('reset', 1)
		print('done')

		print('status: %d' % fpga.read_int('status'))
		print('Sleep one second...')
		time.sleep(1)
		print('status: %d' % fpga.read_int('status'))

	#except KeyboardInterrupt:
		#exit_clean()
	#except:
		#exit_fail()
	finally:
		exit_clean()
