#!/usr/bin/python

import sys
import time
import struct
import katadc
import katcp_wrapper
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui


boffile = 'katadc_dual_snap_2018_Feb_08_1650.bof.gz'

#roach = 'r1807'
#roach = 'r1510'
roach = '10.32.127.33'
katcp_port = 7147
rf_gain = 0


def katadc_init(fpga):
	addr = [0x0000, 0x0001, 0x0002, 0x0003, 0x0009, 0x000A, 0x000B, 0x000E, 0x000F]
	# val  = [0x7FFF, 0xBAFF, 0x007F, 0x807F, 0x03FF, 0x007F, 0x807F, 0x00FF, 0x007F]
	val  = [0x7FFF, 0xB2FF, 0x007F, 0x807F, 0x03FF, 0x007F, 0x807F, 0x00FF, 0x007F]  # 300 MHz
	#if interleaved: val[4] = 0x23FF # Uncomment this line for interleaved mode
	for i in range(len(addr)):
		print('Setting ADC register %04Xh to 0x%04X' % (addr[i], val[i]))
		# Program both ZDOKs (this could be made smarter if needed).
		katadc.spi_write_register(fpga, 0, addr[i], val[i])
		katadc.spi_write_register(fpga, 1, addr[i], val[i])


def update_plots(fpga, curves, hists, specs):
	for zdok in (0, 1):
		for pol in (0, 1):
			scope_name = "u%dp%d" % (zdok, pol)
			snap = fpga.snapshot_get(scope_name, man_trig=True, man_valid=True)
			data = struct.unpack('%db' % snap['length'], snap['data'])
			index = zdok * 2 + pol
			curves[index].setData(data[0:1024])
			y, x = np.histogram(data, 100)
			hists[index].setData(x, y)
			psd = np.abs(np.fft.fft(data)) ** 2
			specs[index].setData(psd[0:256])


# Connect to ROACH
print('Connecting to server %s on port %i ... ' % (roach, katcp_port)),
fpga = katcp_wrapper.FpgaClient(roach, katcp_port, timeout=10)
time.sleep(0.1)

if fpga.is_connected():
	print('ok')
	print('-' * 20)
else:
	print('ERROR connecting to server %s on port %i.\n' % (roach,katcp_port))
	fpga.stop()
	exit()

katadc_init(fpga)

# Program FPGA
# if len(sys.argv) < 2 or sys.argv[1] != '-s' and sys.argv[1] != '--skip':
print('Programming %s ...' % boffile),
fpga.progdev(boffile)
print('done')


'''
# Initialize RF frontend
for zdok in (0, 1):
	for inp in ('I', 'Q'):
		# rf = katadc.rf_fe_get(fpga, zdok, inp)
		# if not rf['enabled']:
		# print('Enable gain in zdok%d %s to %d' % (zdok, inp, rf_gain))
		katadc.rf_fe_set(fpga, zdok, inp, rf_gain)
		time.sleep(0.1)
		print('ZDOK%d %s: ' % (zdok, inp)),
		rf = katadc.rf_fe_get(fpga, zdok, inp)
		print(rf)
'''


# Setup GUI
app = QtGui.QApplication([])
mw = QtGui.QMainWindow()
mw.resize(1600,800)
cw = QtGui.QWidget()
mw.setCentralWidget(cw)

# 2 groups of graph, w0 for zdok0, w1 for zdok1
hb0 = QtGui.QHBoxLayout()
w0 = pg.GraphicsLayoutWidget()
hb0.addWidget(w0)
w1 = pg.GraphicsLayoutWidget()
hb0.addWidget(w1)
w0.addLabel('ZDOK0', row=0, col=0, colspan=2)
w1.addLabel('ZDOK1', row=0, col=0, colspan=2)

# Add plots
curves = []
hists = []
specs = []
for w, i in zip((w0, w0, w1, w1), (0, 1, 0, 1)):
	curves.append(w.addPlot(title='pol%d curve' % i, row=1, col=i).plot())
	hists.append(w.addPlot(title='pol%d hist' % i, row=2, col=i).plot(stepMode=True, fillLevel=0, brush=(0,255,0,150)))
	specs.append(w.addPlot(title='pol%d psd' % i, row=3, col=i).plot())

'''
# Spinbox to adjust gain
hb1 = QtGui.QHBoxLayout()
sbs = []
for zdok in (0, 1):
	for inp in ('I', 'Q'):
		hb1.addStretch()
		hb1.addWidget(QtGui.QLabel('ZDOK%d %s gain:' % (zdok, inp)))
		spinbox = QtGui.QDoubleSpinBox()
		spinbox.setRange(-11.5, 20)
		spinbox.setSingleStep(0.5)
		spinbox.setDecimals(1)
		spinbox.setAlignment(QtCore.Qt.AlignRight)
		spinbox.valueChanged.connect(lambda : )
		sbs.append(spinbox)
		hb1.addWidget(spinbox)
'''

def adjust_gain(zdok, inp, gain):
	print(zdok, inp, gain)
	katadc.rf_fe_set(fpga, zdok, inp, gain)
	time.sleep(0.1)
	print('ZDOK%d %s: ' % (zdok, inp)),
	rf = katadc.rf_fe_get(fpga, zdok, inp)
	print(rf)
	update_plots(fpga, curves, hists, specs)


'''
# ComboBox to adjust gain
hb1 = QtGui.QHBoxLayout()
combos = []
for zdok in (0, 1):
	for inp in ('I', 'Q'):
		hb1.addStretch()
		hb1.addWidget(QtGui.QLabel('ZDOK%d %s gain:' % (zdok, inp)))
		combo = QtGui.QComboBox()
		for v in range(63):
			combo.addItem(str(v / 2.0 - 11.5))
		combo.setCurrentIndex((rf_gain + 11.5) * 2)
		combo.setMaxVisibleItems(20)
		combos.append(combo)
		hb1.addWidget(combo)
'''

btn_refresh = QtGui.QPushButton('Refresh')
btn_refresh.clicked.connect(lambda btn: update_plots(fpga, curves, hists, specs))
hb1 = QtGui.QHBoxLayout()
hb1.addStretch()
hb1.addWidget(btn_refresh)


vbox = QtGui.QVBoxLayout()
vbox.addLayout(hb0)
vbox.addLayout(hb1)

cw.setLayout(vbox)
mw.show()

update_plots(fpga, curves, hists, specs)


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
	import sys
	if sys.flags.interactive != 1 or not hasattr(QtCore, 'PYQT_VERSION'):
		pg.QtGui.QApplication.exec_()
