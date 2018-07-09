#!/usr/bin/env python

import time, struct, sys, logging, socket
import katcp_wrapper, log_handlers
import argparse
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui


bitstream = 'sbh1k_2016_Jun_13_1749.bof.gz'


class attrdict(dict):
    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)
        self.__dict__ = self


roach = '10.0.0.22'
katcp_port = 7147

opts = attrdict(
            nbins = 2**10,
            sfftshift = 2**32-1,
            sgain = 0x0100<<16 | 0x0100,
            acclen = 2**10-1,
            bitsel = 1<<6 | 1<<4 | 1<<2 | 1,
            cfftshift = 2**32-1,
            cgain = 0x0400<<16 | 0x0400
            )


mac_base = (2<<40) + (2<<32)
xgbe_devices = (0, 1, 4, 5, 6, 7)

fabric_ip_string = {}
fabric_ip = {}
fabric_port = {}
for i in xgbe_devices:
    fabric_ip_string[i] = '10.0.%d.227' % (i+1)
    fabric_ip[i] = struct.unpack('!L',socket.inet_aton(fabric_ip_string[i]))[0]  # convert ip to long
    fabric_port[i] = 33333


dest_ip_string = {}
dest_ip = {}
dest_port = {}
for i in xgbe_devices:
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


def get_spectrum_data():
    # get the bit select scope spectrum data...
    #fmtstr = '>' + str(nbins) + 'L'
    scope0 = fpga.snapshot_get('scope0');
    #pol0 = struct.unpack(fmtstr, scope0['data'][0:nbins*4])
    pol0 = numpy.frombuffer(scope0['data'][0:nbins*4], numpy.dtype('>i4'))
    scope1 = fpga.snapshot_get('scope1');
    #pol1 = struct.unpack(fmtstr, scope1['data'][0:nbins*4])
    pol1 = numpy.frombuffer(scope1['data'][0:nbins*4], numpy.dtype('>i4'))
    return pol0, pol1


def get_adcscope_data():
    # get adc scope data
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
    print('A:%4d %5.2f ' % (idx, speclog[idx])),

    snap = fpga.snapshot_get('x8_vacc_scope_B')
    speclin = np.array(struct.unpack('>%dI' % (snap['length']/4), snap['data']))
    speclog = np.log2(speclin+1)
    lines[3].setData(speclog)
    idx = np.argmax(speclog)
    print('B:%4d %5.2f ' % (idx, speclog[idx])),

    snap = fpga.snapshot_get('x8_vacc_scope_C')
    speclin = np.array(struct.unpack('>%di' % (snap['length']/4), snap['data']))
    speclog = np.log2(np.fabs(speclin)+1)
    lines[4].setData(speclog)
    idx = np.argmax(speclog)
    print('C:%4d %5.2f ' % (idx, speclog[idx])),

    snap = fpga.snapshot_get('x8_vacc_scope_D')
    speclin = np.array(struct.unpack('>%di' % (snap['length']/4), snap['data']))
    speclog = np.log2(np.fabs(speclin)+1)
    lines[5].setData(speclog)
    idx = np.argmax(speclog)
    print('D:%4d %5.2f ' % (idx, speclog[idx])),

    # Channelizer scope
    snap = fpga.snapshot_get('x8_chan_scope', man_valid=True)
    p0, p1 = split_snapshot(snap)
    s0 = [p0[2*i]**2 + p0[2*i+1]**2 for i in range(256)]
    s1 = [p1[2*i]**2 + p1[2*i+1]**2 for i in range(256)]
    lines[6].setData(s0)
    lines[7].setData(s1)
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

        '''
        print(roach, katcp_port, bitstream)
        print(opts.nbins, opts.sfftshift, opts.sgain, opts.acclen, opts.bitsel, opts.cfftshift, opts.cgain)
        for i in xgbe_devices:
            print(fabric_ip_string[i], fabric_ip[i], fabric_port[i], mac_base + fabric_ip[i])
            print(dest_ip_string[i], dest_ip[i], dest_port[i])
        print
        '''

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

        print('Configuring spectrometer fft_shift, sfft_shift=0x%X ... ' % opts.sfftshift),
        fpga.write_int('sfft_shift', int(opts.sfftshift))
        print('done')

        print('Configuring spectrometer scale coefficients, sgain=0x%X ... ' % opts.sgain),
        fpga.write_int('sgain', opts.sgain) # in 16_8-16_8 format
        print('done')

        print('Configuring spectrometer bit selection, bit_select=0x%X ... ' % opts.bitsel),
        fpga.write_int('bit_select', opts.bitsel)
        print('done')

        print('Configuring spectrometer accumulation length, acc_len=%d ... ' % opts.acclen),
        fpga.write_int('acc_len',opts.acclen)
        print('done')

        print('Configuring channelizer fft_shift, cfft_shift=0x%X ... ' % opts.cfftshift),
        fpga.write_int('cfft_shift', opts.cfftshift)
        print('done')

        print('Configuring channelizer scale coefficients, cgain=0x%X ... ' % opts.cgain),
        fpga.write_int('cgain', opts.cgain) # in 16_8-16_8 format
        print('done')

        for i in xgbe_devices:
            xgbe_name = 'xgbe%d' % i
            mac_addr = mac_base + fabric_ip[i]
            print('Initialize %s fabric mac: %s, ip: %s, port: %i ...' %
                (xgbe_name, ':'.join(("%012X" % mac_addr)[i:i+2] for i in range(0, 12, 2)),
                 fabric_ip_string[i], fabric_port[i])),
            fpga.tap_start(xgbe_name, xgbe_name + '_core', mac_addr, fabric_ip[i], fabric_port[i])
            print('done')

        fpga.write_int('use_tvg', 1)

        print('Issue reset signal...'),
        fpga.write_int('reset', 0)
        fpga.write_int('reset', 1)
        print('done')

        # set up the figure with a subplot to be plotted
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
        for i in range(6, 8):
            scopenum = i - 6
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
