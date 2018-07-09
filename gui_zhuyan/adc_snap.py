#!/usr/bin/python

import sys
import time
import struct
import re
import numpy as np
import katcp_wrapper
import katadc
import pyqtgraph as pg

# boffile='katadc_zdok0_snap_2016_Mar_10_2010.bof.gz'
boffile='katadc_zdok0_snap_2017_Oct_23_1613.bof.gz'
# boffile='katadc_zdok1_snap_2016_Aug_18_1351.bof.gz'
# boffile='katadc_zdok1_snap_2018_Feb_08_1443.bof.gz'
# boffile='adc5g_zdok0_snap_2016_Mar_11_1753.bof.gz'

# roach = 'r1510'
# roach = 'r1511'
# roach = 'r1807'
roach = '10.32.127.33'
katcp_port = 7147
zdok = 0
m = re.search('zdok(\d)', boffile)
if m:
	zdok = int(m.group(1))


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

if len(sys.argv) < 2 or sys.argv[1] != '-s':
	print('Programming %s ...' % boffile),
	fpga.progdev(boffile)
	print('done')

# Initialize RF frontend
# for inp in ('I', 'Q'):
# 	rf = katadc.rf_fe_get(fpga, zdok, inp)
# 	if not rf['enabled']:
# 		print('Enable gain in zdok%d %s to %d' % (zdok, inp, 0))
# 		katadc.rf_fe_set(fpga, zdok, inp, 0)
# 	else:
# 		print('Already enabled:'),
# 		print(rf)

snap = fpga.snapshot_get('pol0', man_trig=True, man_valid=True)
pol0 = struct.unpack('%db' % snap['length'], snap['data'])
snap = fpga.snapshot_get('pol1', man_trig=True, man_valid=True)
pol1 = struct.unpack('%db' % snap['length'], snap['data'])

win = pg.GraphicsWindow('ADC SNAP')

p0_curve = win.addPlot(title='pol0 curve', row=0, col=0)
p0_curve.plot(pol0[0:1024])
y, x = np.histogram(pol0, 100)
p0_hist = win.addPlot(title='pol0 hist', row=1, col=0)
p0_hist.plot(x, y, stepMode=True, fillLevel=0, brush=(0,255,0,150))

p1_curve = win.addPlot(title='pol1 curve', row=0, col=1)
p1_curve.plot(pol1[0:1024])
y, x = np.histogram(pol1, 100)
p1_hist = win.addPlot(title='pol1 hist', row=1, col=1)
p1_hist.plot(x, y, stepMode=True, fillLevel=0, brush=(0,255,0,150))


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    if sys.flags.interactive != 1 or not hasattr(QtCore, 'PYQT_VERSION'):
        pg.QtGui.QApplication.exec_()
