#!/usr/bin/env python

import time, struct, sys, logging, socket
import katcp_wrapper, log_handlers
import argparse
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui


#bitstream = 'cx8d64_2016_Jun_16_1221.bof.gz'
#bitstream = 'cx8d64_slot1_2016_Nov_25_1812.bof.gz'
bitstream = 'cx8d64_reorder_2016_Nov_29_1503.bof.gz'

class attrdict(dict):
    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)
        self.__dict__ = self


roach = '10.0.0.24'
roach = 'r1510'
katcp_port = 7147

opts = attrdict(
            fftshift    = 2**32-1,
            gain0       = 0x8000,
            gain1       = 0x8000,
            usetvg      = 1
            )


mac_base = (2<<40) + (2<<32)
xgbe_devices = (0, 1, 2, 3)

fabric_ip_string = {}
fabric_ip = {}
fabric_port = {}
for i in xgbe_devices:
    #fabric_ip_string[i] = '10.0.%d.227' % (i+1+4)
    fabric_ip_string[i] = '10.0.%d.227' % (i+1)
    fabric_ip[i] = struct.unpack('!L',socket.inet_aton(fabric_ip_string[i]))[0]  # convert ip to long
    fabric_port[i] = 33333


dest_ip_string = {}
dest_ip = {}
dest_port = {}
for i in xgbe_devices:
    #dest_ip_string[i] = '10.0.%d.127' % (i+1+4)
    dest_ip_string[i] = '10.0.%d.127' % (i+1)
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


def get_adcscope_data():
    adc0 = fpga.snapshot_get('adc_scope0', man_trig=True, man_valid=True);
    fmtstr = '>' + str(adc0['length']) + 'b'
    a0 = struct.unpack(fmtstr, adc0['data'])
    adc1 = fpga.snapshot_get('adc_scope1', man_trig=True, man_valid=True);
    fmtstr = '>' + str(adc1['length']) + 'b'
    a1 = struct.unpack(fmtstr, adc1['data'])
    return a0, a1


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
    adc0, adc1 = get_adcscope_data()
    y, x = np.histogram(adc0, 100)
    lines[0].setData(x, y)
    y, x = np.histogram(adc1, 100)
    lines[1].setData(x, y)

    # Channelizer scope
    snap = fpga.snapshot_get('scope', man_valid=True)
    p0, p1 = split_snapshot(snap)
    s0 = [p0[2*i]**2 + p0[2*i+1]**2 for i in range(64)]
    s1 = [p1[2*i]**2 + p1[2*i+1]**2 for i in range(64)]
    lines[2].setData(s0)
    lines[3].setData(s1)
    idx = np.argmax(np.array(s0))
    print('CH0:%3d %d ' % (idx, s0[idx])),
    idx = np.argmax(np.array(s1))
    print('CH1:%3d %d' % (idx, s1[idx]))

    #print(bin(fpga.read_uint('status')))


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

        for i in xgbe_devices:
            xgbe_name = 'xgbe%d' % i
            print('Configuring %s destination IP and port %s:%i ... ' %
                (xgbe_name, socket.inet_ntoa(struct.pack('!L', dest_ip[i])), dest_port[i])),
            fpga.write_int(xgbe_name + '_dest_ip', dest_ip[i])
            fpga.write_int(xgbe_name + '_dest_port', dest_port[i])
            print('done')

        print('Configuring spectrometer fft_shift, fft_shift=0x%X ... ' % opts.fftshift),
        fpga.write_int('fft_shift', int(opts.fftshift))
        print('done')

        print('Configuring spectrometer scale coefficients, gain0=0x%X gain1=0x%X... ' % (opts.gain0, opts.gain1)),
        fpga.write_int('gain0', opts.gain0)
        fpga.write_int('gain1', opts.gain1)     # in ufix18_12 format
        print('done')

        for i in xgbe_devices:
            #xgbe_name = 'ens1p%d' % i
            xgbe_name = 'ens0p%d' % i
            mac_addr = mac_base + fabric_ip[i]
            print('Initialize %s fabric mac: %s, ip: %s, port: %i ...' %
                (xgbe_name, ':'.join(("%012X" % mac_addr)[i:i+2] for i in range(0, 12, 2)),
                 fabric_ip_string[i], fabric_port[i])),
            fpga.tap_start(xgbe_name, xgbe_name + '_core', mac_addr, fabric_ip[i], fabric_port[i])
            print('done')

        fpga.write_int('use_tvg', opts.usetvg)

        print('Issue reset signal...'),
        fpga.write_int('reset', 0)
        fpga.write_int('reset', 1)
        print('done')

        #while True:
            #print(bin(fpga.read_uint('status')))
            #time.sleep(1)

        # set up the figure with a subplots to be plotted
        win = pg.GraphicsWindow(title='mmm')
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
        for i in range(2, 4):
             scopenum = i - 2
             plt = win.addPlot(title='CHAN Scope %d' % scopenum)
             plts.append(plt)
             lines.append(plt.plot())

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
