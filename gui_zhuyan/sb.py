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

roach = 'r1511'
katcp_port = 7147
mac_base = (2<<40) + (2<<32)	# 0x020200000000


class attrdict(dict):
	def __init__(self, **kwargs):
		dict.__init__(self, **kwargs)
		self.__dict__ = self

opts = attrdict(
			nbins = 4 * 2**10,
			fftshift = 2**32-1,
			gain = 0x0100<<16 | 0x0100,
			acclen = 100,
			bitsel = 1<<6 | 2<<4 | 2<<2 | 2,
			)


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
	# Workaround for tgtap:
	#   write destination ip address entry in arp table to all 0 mac address
	#   instead of broadcast address filled by tgtap
	fpga.write(devname, '\0'*8, 0x3000 + 8 * (dest_ip_addr & 0xFF))


def exit_clean():
	try:
		fpga.stop()
	except:
		pass
	exit()


def exit_fail(e):
	print('FAILURE DETECTED.')
	print('Exception:')
	print(e)
	print('Log entries:')
	lh.printMessages()
	exit_clean()


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
	pol0, pol1 = split_snapshot(snap)
	y, x = np.histogram(pol0, 100)
	lines[0].setData(x, y)
	y, x = np.histogram(pol1, 100)
	lines[1].setData(x, y)

	# ADC curve
	# lines[2].setData(pol0[0:1024])
	lines[2].setData(pol0)
	lines[3].setData(pol1[0:1024])

	# Spectrometer scope
	snap = fpga.snapshot_get('x8_vacc_scope_A')
	speclin = np.array(struct.unpack('>%dI' % (snap['length']/4), snap['data']))
	speclog = np.log2(speclin+1)
	lines[4].setData(speclog)
	idx = np.argmax(speclog)
	print('A:%4d %5.2f, %5.2f ' % (idx, speclog[idx], np.mean(speclog))),

	snap = fpga.snapshot_get('x8_vacc_scope_B')
	speclin = np.array(struct.unpack('>%dI' % (snap['length']/4), snap['data']))
	speclog = np.log2(speclin+1)
	lines[5].setData(speclog)
	idx = np.argmax(speclog)
	print('B:%4d %5.2f, %5.2f ' % (idx, speclog[idx], np.mean(speclog))),

	snap = fpga.snapshot_get('x8_vacc_scope_C')
	speclin = np.array(struct.unpack('>%di' % (snap['length']/4), snap['data']))
	speclog = np.log2(np.fabs(speclin)+1)
	lines[6].setData(speclog)
	idx = np.argmax(speclog)
	print('C:%4d %5.2f, %5.2f ' % (idx, speclog[idx], np.mean(speclog))),

	snap = fpga.snapshot_get('x8_vacc_scope_D')
	speclin = np.array(struct.unpack('>%di' % (snap['length']/4), snap['data']))
	speclog = np.log2(np.fabs(speclin)+1)
	lines[7].setData(speclog)
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
		parser.add_argument('-v', '--view', action='store_true', default=False, help='View only')
		args = parser.parse_args()

		print('Connecting to server %s on port %i... ' % (roach, katcp_port)),
		fpga = katcp_wrapper.FpgaClient(roach, katcp_port, timeout=10, logger=logger)
		time.sleep(0.1)

		if fpga.is_connected():
			print('ok')
		else:
			print('ERROR connecting to server %s on port %i.\n' % (roach,katcp_port))
			exit_fail()

		print('-' * 20)

		if not args.skip and  not args.view:
			print('Programming FPGA with  %s ... ' % bitstream),
			fpga.progdev(bitstream)
			print('done')

		if not args.view:
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

			init_10gbe('xgbe0', '192.168.11.227', 33333, '192.168.11.127', 12345)
			init_10gbe('xgbe1', '192.168.12.227', 33333, '192.168.11.127', 12345)

			init_10gbe('xgbe4', '192.168.15.227', 33333, '192.168.15.127', 12345)
			init_10gbe('xgbe5', '192.168.16.227', 33333, '192.168.16.127', 12345)
			init_10gbe('xgbe6', '192.168.17.227', 33333, '192.168.17.127', 12345)
			init_10gbe('xgbe7', '192.168.18.227', 33333, '192.168.18.127', 12345)

			fpga.write_int('use_tvg', 0)

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
		win.nextRow()
		for i in range(2, 4):
			scopenum = i - 2
			plt = win.addPlot(title='ADC Curve %d' % scopenum)
			plts.append(plt)
			lines.append(plt.plot())
		win.nextRow()
		for i in range(4, 8):
			scopenum = i - 4
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
