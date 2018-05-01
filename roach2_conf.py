#!/usr/bin/python

import time, struct, sys, logging, socket
from corr import katcp_wrapper, log_handlers
import argparse
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui


#bitstream = 'mb1k_2017_Oct_05_0247.bof.gz'
bitstream = 'mb4k_2017_Oct_06_2340.bof'
#bitstream = 'mb4k-v146.bof.gz'

#roach2 = 'r1807'
#roach2 = 'r2d021403.bl.pvt' # (10.0.1.169) mounted on blh2
#roach2 = 'r2d021403' # 10.0.1.170 mounted on acme1
roach2 = 'r2d021403.s6.pvt' # (10.0.1.169) mounted on asa2

katcp_port = 7147

spec_scope_names = ('AA', 'BB', 'CR', 'CI')


class attrdict(dict):
	def __init__(self, **kwargs):
		dict.__init__(self, **kwargs)
		self.__dict__ = self

# integration time 4096*2*acclen/1024M = 8192*32/1024M = 256 us
# acclen start from 0, if acclen=7, use 8 to calculate
opts = attrdict(
			nbins = 4 * 2**10,
			fftshift = 2**32-1,
			gain = 0x0200<<16 | 0x0200,
			#acclen = 31,
			acclen = 7,
			bitsel = 2<<6 | 2<<4 | 2<<2 | 2,
			)


mac_base = (2<<40) + (2<<32)
xgbe_devices = (0, 1, 2, 3)

fabric_ip_string = {}
fabric_ip = {}
fabric_port = {}
for i in xgbe_devices:
	#fabric_ip_string[i] = '10.0.%d.227' % (i+5)
	fabric_ip_string[i] = '10.10.%d.%d' % (i+12,i+12) # snb11
	fabric_ip[i] = struct.unpack('!L',socket.inet_aton(fabric_ip_string[i]))[0]  # convert ip to long
	fabric_port[i] = 33333


dest_ip_string = {}
dest_ip = {}
dest_port = {}
for i in xgbe_devices:
	#dest_ip_string[i] = '10.0.%d.127' % (i+5)
	dest_ip_string[i] = '10.10.%d.%d' % (i+12,i+2)
	dest_ip[i] = struct.unpack('!L', socket.inet_aton(dest_ip_string[i]))[0]
	dest_port[i] = 12345


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
	adc = 'zdok0_scope'
	unit = 'u0'
	#adc = 'zdok1_scope'
	#unit = 'u1'

	# ADC histogram
	snap = fpga.snapshot_get(adc, man_trig=True, man_valid=True)
	adc0, adc1 = split_snapshot(snap)
	y, x = np.histogram(adc0, 100)
	lines[0].setData(x, y)
	y, x = np.histogram(adc1, 100)
	lines[1].setData(x, y)

	# Spectrometer scope
	for i in range(2, 4):
		scopename = unit + '_x4_vacc_scope_' + spec_scope_names[i-2]
		snap = fpga.snapshot_get(scopename, man_valid=True)
		speclin = np.array(struct.unpack('>%dI' % (snap['length']/4), snap['data']))
		speclog = np.log2(speclin+1)
		lines[i].setData(speclog)
		idx = np.argmax(speclog)

	for i in range(4, 6):
		scopename = unit + '_x4_vacc_scope_' + spec_scope_names[i-2]
		snap = fpga.snapshot_get(scopename, man_valid=True)
		speclin = np.array(struct.unpack('>%di' % (snap['length']/4), snap['data']))
		speclog = np.log2(np.fabs(speclin)+1)
		lines[i].setData(speclog)
		idx = np.argmax(speclog)



#START OF MAIN:

if __name__ == '__main__':

	try:
		lh = log_handlers.DebugLogHandler()
		logger = logging.getLogger(roach2)
		logger.addHandler(lh)
		logger.setLevel(10)

		parser = argparse.ArgumentParser()
		parser.add_argument('-s', '--skip', action='store_true', default=False, help='Skip programming FPGA')
		args = parser.parse_args()

		#print(roach2, katcp_port, bitstream)
		#print(opts.nbins, opts.fftshift, opts.gain, opts.acclen, opts.bitsel)
		#for i in xgbe_devices:
			#print(fabric_ip_string[i], fabric_ip[i], fabric_port[i], mac_base + fabric_ip[i])
			#print(dest_ip_string[i], dest_ip[i], dest_port[i])
		#print

		print('Connecting to server %s on port %i... ' % (roach2, katcp_port)),
		fpga = katcp_wrapper.FpgaClient(roach2, katcp_port, timeout=10, logger=logger)
		time.sleep(0.1)

		if fpga.is_connected():
			print('ok')
		else:
			print('ERROR connecting to server %s on port %i.\n' % (roach2,katcp_port))
			exit_fail()

		print('-' * 20)

		if not args.skip:
			print('Programming FPGA with  %s ... ' % bitstream),
			fpga.progdev(bitstream)
			print('done')

		'''dest_mac = {}
		arptable = {}
		for i in xgbe_devices:
			xgbe_name = 'xgbe%d' % i

			dest_mac[i] = mac_base+dest_ip[i]
			#dest_mac[i] = 0x020210101002 + i
			arptable[i] = [dest_mac[i]]*256 
			print('Configuring %s mac: %i destination IP and port %s:%i ... ' %
				(xgbe_name,dest_mac[i], socket.inet_ntoa(struct.pack('!L', dest_ip[i])), dest_port[i])),
				#(xgbe_name,':'.join(("%012X" % dest_mac)[j:j+2] for j in range(0, 12, 2)), socket.inet_ntoa(struct.pack('!L', dest_ip[i])), dest_port[i])),
			fpga.write_int(xgbe_name + '_dest_ip', dest_ip[i])
			fpga.write_int(xgbe_name + '_dest_port', dest_port[i])
			print('done')'''

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

		for i in xgbe_devices:
			xgbe_name = 'xgbe%d' % i
			#mac_addr = mac_base + fabric_ip[i]
			#dest_mac = mac_base+dest_ip[i]
			mac_addr = mac_base + (10<<24) + (10<<16)+(10<<8)+i+12
			dest_mac = mac_base+(10<<24) + (10<<16)+(10<<8)+i+2
			arptable = [dest_mac]*256
			print('Configuring %s dest mac: %s destination IP and port %s:%i ... ' %
                               (xgbe_name,':'.join(("%012X" % dest_mac)[j:j+2] for j in range(0, 12, 2)), socket.inet_ntoa(struct.pack('!L', dest_ip[i])), dest_port[i])),
                        fpga.write_int(xgbe_name + '_dest_ip', dest_ip[i])
                        fpga.write_int(xgbe_name + '_dest_port', dest_port[i])
                        print('done')

			print('Initialize %s fabric mac: %s, ip: %s, port: %i ...' %
				(xgbe_name, ':'.join(("%012X" % mac_addr)[i:i+2] for i in range(0, 12, 2)),
				 fabric_ip_string[i], fabric_port[i])),
			#fpga.tap_start(xgbe_name, xgbe_name + '_core', mac_addr, fabric_ip[i], fabric_port[i])
			fpga.config_10gbe_core(xgbe_name + '_core',mac_addr,fabric_ip[i], fabric_port[i],arptable)
			fpga.print_10gbe_core_details(xgbe_name + '_core')
			print('done')

		fpga.write_int('use_tvg', 0b00)
		#fpga.write_int('use_tvg', 0b11)

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
			if i%2 == 1:
				win.nextRow()
		for i in range(2, 6):
			scopenum = i - 2
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
		#timer.start(1000)
		timer.start(100)

		QtGui.QApplication.instance().exec_()

	except KeyboardInterrupt:
		exit_clean()
	except Exception as e:
		exit_fail(e)
	finally:
		exit_clean()
