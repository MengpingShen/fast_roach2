#!/usr/bin/env python

import time, struct, sys, logging, socket
import katcp_wrapper, log_handlers
import argparse
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui


#bitstream = 'sb1k_2016_Oct_21_1640.bof.gz'
#bitstream = 'sb2k_2017_Jan_21_1219.bof.gz'
bitstream = 'sb4k_2017_Jan_21_1934.bof.gz'
#bitstream = 'sb8k_2016_Oct_29_1539.bof.gz'

class attrdict(dict):
	def __init__(self, **kwargs):
		dict.__init__(self, **kwargs)
		self.__dict__ = self


roach = 'r1511'
katcp_port = 7147

opts = attrdict(
			nbins = 4 * 2**10,
			fftshift = 2**32-1,
			gain = 0x0100<<16 | 0x0100,
			acclen = 100,
			bitsel = 1<<6 | 2<<4 | 2<<2 | 2,
			)


mac_base = (2<<40) + (2<<32)

def init_10gbe(dev, ip, port, dest_ip, dest_port):
	ip_addr, = struct.unpack('!L',socket.inet_aton(ip))
	mac_addr = mac_base + ip_addr
	devname = dev + '_core'
	print('Initializing %s fabric mac: %s, ip: %s, port: %i ...' %
			(dev, ':'.join(("%012X" % mac_addr)[i:i+2] for i in range(0, 12, 2)), ip, port)),
	fpga.tap_start(dev, devname, mac_addr, ip_addr, port)
	print('done')
	dest_ip_addr, = struct.unpack('!L',socket.inet_aton(dest_ip))
	print('Configuring %s destination IP and port %s:%i ... ' %
			(dev, socket.inet_ntoa(struct.pack('!L', dest_ip_addr)), dest_port)),
	fpga.write_int(dev + '_dest_ip', dest_ip_addr)
	fpga.write_int(dev + '_dest_port', dest_port)
	print('done')
	# Write destination ip address entry in arp table to 0 instead of broadcast address by tgtap
	fpga.write(devname, '\0'*8, 0x3000 + 8 * (dest_ip_addr & 0xFF))

'''
def init_10gbe(dev, ip, port, dest_ip, dest_port):
	# zero out arp table
	devname = dev+'_core'
	#fpga.write(devname, '\0'*2048, 0x3000)
	fpga.write(devname, '\x00\x00\x03\x04\x05\x06\x07\x08', 0x3000 + 8 * 127)
	#fpga.write(devname, '\xf8\xbc\x12\x0d\x77\x80\x00\x00', 0x3000 + 8 * 127)
	# mac
	#fpga.write(devname, '\0'*8, 0x0)
	ip_addr, = struct.unpack('!L',socket.inet_aton(ip))
	mac_addr = mac_base + ip_addr
	fpga.write(devname, mac_addr, 0x0)
	# ip
	#fpga.write(devname, '\0'*4, 0x10)
'''

def exit_fail(e):
	print('FAILURE DETECTED.')
	print('Exception:')
	print(e)
	print('Log entries:')
	lh.printMessages()
	try:
		fpga.stop()
	except: pass
	exit()


def exit_clean():
	try:
		fpga.stop()
	except: pass
	exit()


def split_snapshot(snap):
	len = snap['length']
	all = struct.unpack('%db'%len, snap['data'])
	p0 = []
	p1 = []
	for i in range(len/16):
		p0 = p0 + list(all[i*16   :     i*16+8])
		p1 = p1 + list(all[i*16+8 : (i+1)*16])
	return p0, p1

def plot_anim():
	global fpga, plts, lines

	# ADC histogram
	snap = fpga.snapshot_get('zdok0_scope', man_trig=True, man_valid=True)
	adc0, adc1 = split_snapshot(snap)
	y, x = np.histogram(adc0, 100)
	lines[0].setData(x, y)
	y, x = np.histogram(adc1, 100)
	lines[1].setData(x, y)

	# Spectrometer scope
	snap = fpga.snapshot_get('x8_vacc_scope_A')
	speclin = np.array(struct.unpack('>%dI' % (snap['length']/4), snap['data']))
	speclog = np.log2(speclin+1)
	lines[2].setData(speclog)
	idx = np.argmax(speclog)
	print('A:%4d %5.2f, %5.2f ' % (idx, speclog[idx], np.mean(speclog))),

	snap = fpga.snapshot_get('x8_vacc_scope_B')
	speclin = np.array(struct.unpack('>%dI' % (snap['length']/4), snap['data']))
	speclog = np.log2(speclin+1)
	lines[3].setData(speclog)
	idx = np.argmax(speclog)
	print('B:%4d %5.2f, %5.2f ' % (idx, speclog[idx], np.mean(speclog))),

	snap = fpga.snapshot_get('x8_vacc_scope_C')
	speclin = np.array(struct.unpack('>%di' % (snap['length']/4), snap['data']))
	speclog = np.log2(np.fabs(speclin)+1)
	lines[4].setData(speclog)
	idx = np.argmax(speclog)
	print('C:%4d %5.2f, %5.2f ' % (idx, speclog[idx], np.mean(speclog))),

	snap = fpga.snapshot_get('x8_vacc_scope_D')
	speclin = np.array(struct.unpack('>%di' % (snap['length']/4), snap['data']))
	speclog = np.log2(np.fabs(speclin)+1)
	lines[5].setData(speclog)
	idx = np.argmax(speclog)
	print('D:%4d %5.2f, %5.2f ' % (idx, speclog[idx], np.mean(speclog))),

	print(bin(fpga.read_uint('status')))


#START OF MAIN:

if __name__ == '__main__':

	try:
		lh = log_handlers.DebugLogHandler()
		logger = logging.getLogger(roach)
		logger.addHandler(lh)
		logger.setLevel(10)

		parser = argparse.ArgumentParser()
		parser.add_argument('-s', '--skip', action='store_true', default=False, help='Skip programming FPGA')
		args = parser.parse_args()

		#print(roach, katcp_port, bitstream)
		#print(opts.nbins, opts.fftshift, opts.gain, opts.acclen, opts.bitsel)
		#for i in xgbe_devices:
			#print(fabric_ip_string[i], fabric_ip[i], fabric_port[i], mac_base + fabric_ip[i])
			#print(dest_ip_string[i], dest_ip[i], dest_port[i])
		#print

		print('Connecting to server %s on port %i... ' % (roach, katcp_port)),
		fpga = katcp_wrapper.FpgaClient(roach, katcp_port, timeout=10, logger=logger)
		time.sleep(0.1)

		# '''
		if fpga.is_connected():
			print('ok')
		else:
			print('ERROR connecting to server %s on port %i.\n' % (roach,katcp_port))
			exit_fail()

		print('-' * 20)

		if not args.skip:
			print('Programming FPGA with  %s ... ' % bitstream),
			fpga.progdev(bitstream)
			print('done')

		print('Configuring spectrometer fft_shift, fft_shift=0x%X ... ' % opts.fftshift),
		fpga.write_int('fft_shift', int(opts.fftshift))
		print('done')

		print('Configuring spectrometer scale coefficients, gain=0x%X ... ' % opts.gain),
		fpga.write_int('gain', opts.gain) # in 16_8-16_8 format
		print('done')

		print('Configuring spectrometer bit selection, bit_select=0x%X ... ' % opts.bitsel),
		fpga.write_int('bit_select', opts.bitsel)
		print('done')

		print('Configuring spectrometer accumulation length, acc_len=%d ... ' % opts.acclen),
		fpga.write_int('acc_len',opts.acclen)
		print('done')

		#############################################################
		# CLEAR ARP TABLE
        #assemble struct for header stuff...
        #0x00 - 0x07: My MAC address
        #0x08 - 0x0b: Not used
        #0x0c - 0x0f: Gateway addr
        #0x10 - 0x13: my IP addr
        #0x14 - 0x17: Not assigned
        #0x18 - 0x1b: Buffer sizes
        #0x1c - 0x1f: Not assigned
        #0x20       : soft reset (bit 0)
        #0x21       : fabric enable (bit 0)
        #0x22 - 0x23: fabric port
        #0x24 - 0x27: XAUI status (bit 2,3,4,5=lane sync, bit6=chan_bond)
        #0x28 - 0x2b: PHY config
        #0x28       : RX_eq_mix
        #0x29       : RX_eq_pol
        #0x30 - 0x33: Multicast IP RX base address
        #0x34       : Multicast IP RX IP mask
        #0x2a       : TX_preemph
        #0x2b       : TX_diff_ctrl
        #0x1000     : CPU TX buffer
        #0x2000     : CPU RX buffer
        #0x3000     : ARP tables start
		for i in (0, 1, 4, 5, 6, 7):
			ifname = ('xgbe%d' % i) + '_core'
			arp_array = [0] * 256
			arp_table = struct.pack('>256Q', *arp_array)
			fpga.write( ifname, arp_table, offset=0x3000)
		#############################################################

		init_10gbe('xgbe0', '10.0.1.228', 33333, '10.0.1.128', 12345)
		init_10gbe('xgbe1', '10.0.2.228', 33333, '10.0.2.128', 12345)

		init_10gbe('xgbe4', '10.0.5.228', 33333, '10.0.5.128', 12345)
		init_10gbe('xgbe5', '10.0.6.228', 33333, '10.0.6.128', 12345)
		init_10gbe('xgbe6', '10.0.7.228', 33333, '10.0.7.128', 12345)
		init_10gbe('xgbe7', '10.0.8.228', 33333, '10.0.8.128', 12345)

		fpga.write_int('use_tvg', 1)

		print('Issue reset signal...'),
		fpga.write_int('reset', 0)
		fpga.write_int('reset', 1)
		print('done')

		# set up the figure with a subplot to be plotted
		win = pg.GraphicsWindow(title='Single Beam')
		win.resize(1000, 800)
		plts = []
		lines = []
		for i in range(0, 2):
			scopenum = i
			plt = win.addPlot(title='ADC Hist %d' % scopenum)
			plts.append(plt)
			lines.append(plt.plot(stepMode=True, fillLevel=0, brush=(0,255,0,150)))
			if i%2 == 1:
				win.nextRow()
		for i in range(2, 6):
			scopenum = i - 2
			plt = win.addPlot(title='SPEC Scope %d' % scopenum)
			plts.append(plt)
			plt.showGrid(y=True)
			plt.setYRange(0, 32)
			plt.getAxis('left').setTicks([[(0, '0'), (8, '2^8'), (16, '2^16'), (24, '2^24'), (32, '2^32')]])
			lines.append(plt.plot())
			if i%2 == 1:
				win.nextRow()

		print('Plot started.')
		plot_anim()

		# start the process
		timer = QtCore.QTimer()
		timer.timeout.connect(plot_anim)
		timer.start(1000)

		QtGui.QApplication.instance().exec_()

	except KeyboardInterrupt:
		exit_clean()
	except Exception as e:
		exit_fail(e)
	finally:
		exit_clean()
