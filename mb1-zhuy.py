#!/usr/bin/env python

import time, struct, sys, logging, socket
from corr import katadc,katcp_wrapper, log_handlers
#import katadc
import argparse
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui


bitstream = 'mb4k-v146.bof.gz'
#bitstream = 'mb4k_2017_Oct_06_2340.bof.gz'
#bitstream = 'mb1k_2017_Aug_25_1643.bof.gz'

#roach = '11.128.2.7'
roach = 'r1807'
katcp_port = 7147

spec_scope_names = ('AA', 'BB', 'CR', 'CI')


class attrdict(dict):
	def __init__(self, **kwargs):
		dict.__init__(self, **kwargs)
		self.__dict__ = self

opts = attrdict(
			nbins = 4 * 2**10,
			fftshift = 2**32-1,
			#gain = 0x0100<<16 | 0x0100,
			gain = 0x0200<<16 | 0x0200,
			acclen = 7,
			#acclen = 32,
			bitsel = 2<<6 | 2<<4 | 2<<2 | 2,
			)


mac_base = (2<<40) + (2<<32)


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


def init_10gbe(dev, ip, port, dest_ip, dest_port):
	#mip = '192.168.3.227'
	#ip_addr, = struct.unpack('!L',socket.inet_aton(mip))
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
	# Workaround for tgtap:
	#   write destination ip address entry in arp table to all 0 mac address
	#   instead of broadcast address filled by tgtap
	fpga.write(devname, '\0'*8, 0x3000 + 8 * (dest_ip_addr & 0xFF))


'''
def split_snapshot(snap):
	len = snap['length']
	all = struct.unpack('%db'%len, snap['data'])
	p0 = []
	p1 = []
	for i in range(len/8):
		p0 = p0 + list(all[i*8   :     i*8+4])
		p1 = p1 + list(all[i*8+4 : (i+1)*8  ])
	return p0, p1
'''
def split_snapshot(snap):
	len = snap['length']
	all = struct.unpack('%db'%len, snap['data'])
	segments = np.array(all).reshape(-1, 4)
	p0 = segments[0::2, :].flatten()
	p1 = segments[1::2, :].flatten()
	return p0, p1


def plot_anim():
	global fpga, plts, lines
	adc = 'zdok0_scope'
	unit = 'u0'
	#adc = 'zdok1_scope'
	#unit = 'u1'

	# ADC histogram
	snap = fpga.snapshot_get(adc, man_trig=True, man_valid=True)
	pol0, pol1 = split_snapshot(snap)
	y, x = np.histogram(pol0, 100)
	lines[0].setData(x, y)
	y, x = np.histogram(pol1, 100)
	lines[1].setData(x, y)

	# ADC curve
	lines[2].setData(pol0[0:256])
	lines[3].setData(pol1[0:256])

	# Spectrometer scope
	for i in range(4, 6):
		scopename = unit + '_x4_vacc_scope_' + spec_scope_names[i-4]
		snap = fpga.snapshot_get(scopename, man_valid=True)
		speclin = np.array(struct.unpack('>%dI' % (snap['length']/4), snap['data']))
		speclog = np.log2(speclin+1)
		lines[i].setData(speclog)
		idx = np.argmax(speclog)

	for i in range(6, 8):
		scopename = unit + '_x4_vacc_scope_' + spec_scope_names[i-4]
		snap = fpga.snapshot_get(scopename, man_valid=True)
		speclin = np.array(struct.unpack('>%di' % (snap['length']/4), snap['data']))
		speclog = np.log2(np.fabs(speclin)+1)
		lines[i].setData(speclog)
		idx = np.argmax(speclog)



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

		# Initialize all KatADC RF frontends
		print('Initialize KatADC RF frontend ...')
		for zdok in (0, 1):
			for inp in ('I', 'Q'):
				rf = katadc.rf_fe_get(fpga, zdok, inp)
				if not rf['enabled']:
					print('Enable gain in zdok%d %s to %d' % (zdok, inp, 0))
					katadc.rf_fe_set(fpga, zdok, inp, 0)
		print('done')

		for unit in ('u0', 'u1'):
			print('Configuring spectrometer "%s" fft_shift, fft_shift=0x%X ... ' % (unit, opts.fftshift)),
			fpga.write_int(unit + '_fft_shift', int(opts.fftshift))
			print('done')

			print('Configuring spectrometer "%s" scale coefficients, gain=0x%X ... ' % (unit, opts.gain)),
			fpga.write_int(unit + '_gain', opts.gain) # in 16_8-16_8 format
			print('done')

			print('Configuring spectrometer "%s" bit selection, bit_select=0x%X ... ' % (unit, opts.bitsel)),
			fpga.write_int(unit + '_bit_select', opts.bitsel)
			print('done')

			print('Configuring spectrometer "%s" accumulation length, acc_len=%d ... ' % (unit, opts.acclen)),
			fpga.write_int(unit + '_acc_len',opts.acclen)
			print('done')

		fpga.write_int('use_tvg', 0b11)

		#init_10gbe('xgbe0', '192.168.1.227', 33333, '192.168.1.127', 12345)
		#init_10gbe('xgbe1', '192.168.2.227', 33333, '192.168.2.127', 12345)
		#init_10gbe('xgbe2', '192.168.3.227', 33333, '192.168.3.127', 12345)
		#init_10gbe('xgbe3', '192.168.4.227', 33333, '192.168.4.127', 12345)
		init_10gbe('xgbe0', '192.168.1.227', 33333, '239.1.0.1', 12345)
		init_10gbe('xgbe1', '192.168.2.227', 33333, '239.1.0.2', 12345)
		init_10gbe('xgbe2', '192.168.3.227', 33333, '239.1.0.3', 12346)
		init_10gbe('xgbe3', '192.168.4.227', 33333, '239.1.0.4', 12346)

		init_10gbe('xgbe4', '192.168.5.227', 33333, '192.168.5.127', 12345)
		init_10gbe('xgbe5', '192.168.5.227', 33334, '192.168.5.127', 12346)
		init_10gbe('xgbe6', '192.168.5.227', 33335, '192.168.5.127', 12347)
		init_10gbe('xgbe7', '192.168.5.227', 33336, '192.168.5.127', 12348)

		print('Issue reset signal...'),
		fpga.write_int('reset', 0b00)
		fpga.write_int('reset', 0b11)
		print('done')

		# set up the figure with a subplot to be plotted
		win = pg.GraphicsWindow(title='Multi-beam')
		win.resize(1000, 800)
		plts = []
		lines = []
		for i in range(0, 2):
			scopenum = i
			plt = win.addPlot(title='ADC Hist %d' % scopenum)
			plts.append(plt)
			lines.append(plt.plot(stepMode=True, fillLevel=0, brush=(0,255,0,150)))
		win.nextRow()
		for i in range(2, 4):
			scopenum = i - 2
			plt = win.addPlot(title='ADC Curve %d' % scopenum)
			plts.append(plt)
			lines.append(plt.plot())
		win.nextRow()
		for i in range(4, 8):
			scopenum = i - 4
			plt = win.addPlot(title='SPEC Scope ' + spec_scope_names[scopenum])
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
