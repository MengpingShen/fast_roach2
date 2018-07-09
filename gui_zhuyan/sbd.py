
import sys
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import time, struct, sys, logging, socket, argparse
import katcp_wrapper, log_handlers


#bitstream = 'sb1k_2016_Oct_21_1640.bof.gz'
#bitstream = 'sb8k_2016_Oct_29_1539.bof.gz'
# bitstream = 'sb1kd_2017_Apr_05_1235.bof.gz'
# bitstream = 'sbd1k_2017_May_02_1337.bof.gz'
bitstream = 'sbd1k-2.1G_2017_May_10_1553.bof.gz'

roach = 'r1510'
katcp_port = 7147


class attrdict(dict):
    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)
        self.__dict__ = self

opts = attrdict(nbins = 1 * 2**10,
                fftshift = 2**32-1,
                gain = 0x0100<<16 | 0x0100,
                acclen = 10,
                bitsel = 0b01010101)


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


def do_config(fpga):
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

    print('Configuring spectrometer scale coefficients, gain=0x%X ... ' % opts.gain),
    fpga.write_int('gain', opts.gain) # in 16_8-16_8 format
    print('done')

    print('Configuring spectrometer bit selection, bit_select=0x%X ... ' % opts.bitsel),
    fpga.write_int('bit_select', opts.bitsel)
    print('done')

    print('Configuring spectrometer accumulation length, acc_len=%d ... ' % opts.acclen),
    fpga.write_int('acc_len',opts.acclen)
    print('done')

    for i in xgbe_devices:
        xgbe_name = 'xgbe%d' % i
        mac_addr = mac_base + fabric_ip[i]
        print('Initialize %s fabric mac: %s, ip: %s, port: %i ...' %
            (xgbe_name, ':'.join(("%012X" % mac_addr)[i:i+2] for i in range(0, 12, 2)),
             fabric_ip_string[i], fabric_port[i])),
        fpga.tap_start(xgbe_name, xgbe_name + '_core', mac_addr, fabric_ip[i], fabric_port[i])
        print('done')

    fpga.write_int('use_tvg', 0b1)


def do_reset(fpga):
    print('Issue reset signal...'),
    fpga.write_int('reset', 0)
    fpga.write_int('reset', 1)
    print('done')


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


class SBDWin(QtGui.QWidget):

    def __init__(self, fpga):
        super(SBDWin, self).__init__()
        self.fpga = fpga
        self.tickfont = QtGui.QFont()
        self.tickfont.setPointSize(9)
        self.init_widgets()
        self.init_plots()
        self.yscale_type = ''
        self.set_yscale_type('logarithm')
        self.setGeometry(200, 200, 1280, 800)
        self.setWindowTitle('SBDWin')
        do_config(self.fpga)
        do_reset(self.fpga)
        self.show()
        # start update
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.plot_anim)
        self.timer.setInterval(500)
        self.timer.start()
        self.scope = {}
        self.passband = {}


    def init_widgets(self):
        lbl_nbins = QtGui.QLabel('nbins:')
        self.combo_nbins = QtGui.QComboBox()
        for i in range(11):
            self.combo_nbins.addItem('%dk' % (1<<i))
        self.combo_nbins.setCurrentIndex(6)

        lbl_nacc = QtGui.QLabel('nacc:')
        self.edit_nacc = QtGui.QSpinBox()

        lbl_tacc = QtGui.QLabel('tacc:')
        self.lbl_tacc = QtGui.QLabel('0.123s')

        hb1 = QtGui.QHBoxLayout()
        hb1.addWidget(lbl_nbins)
        hb1.addWidget(self.combo_nbins)

        hb2 = QtGui.QHBoxLayout()
        hb2.addWidget(lbl_nacc)
        hb2.addWidget(self.edit_nacc)

        hb3 = QtGui.QHBoxLayout()
        hb3.addWidget(lbl_tacc)
        hb3.addWidget(self.lbl_tacc)

        self.rb_log = QtGui.QRadioButton("L&ogarithm")
        self.rb_lin = QtGui.QRadioButton("L&inear")
        self.rb_log.toggle()
        self.rb_log.toggled.connect(self.on_logarithm_yscale)
        self.btn_program = QtGui.QPushButton("Con&figure")
        self.btn_program.clicked.connect(self.on_config)
        self.btn_capture = QtGui.QPushButton("Ca&pture")
        self.btn_capture.clicked.connect(self.on_capture)
        self.btn_clear = QtGui.QPushButton("&Clear")
        self.btn_clear.clicked.connect(self.on_clear)
        self.btn_reset = QtGui.QPushButton("&Reset")
        self.btn_reset.clicked.connect(self.on_reset)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hb1)
        vbox.addLayout(hb2)
        vbox.addLayout(hb3)
        vbox.addStretch(10)
        vbox.addWidget(self.rb_log)
        vbox.addWidget(self.rb_lin)
        vbox.addStretch(1)
        vbox.addWidget(self.btn_program)
        vbox.addWidget(self.btn_capture)
        vbox.addWidget(self.btn_clear)
        vbox.addWidget(self.btn_reset)

        self.plotwin = pg.GraphicsLayoutWidget()

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.plotwin)
        hbox.addSpacing(15)
        hbox.addLayout(vbox)

        self.setLayout(hbox)


    def set_yscale_type(self, scale_type):
        if self.yscale_type == scale_type:
            return
        self.yscale_type = scale_type
        if scale_type == 'logarithm':
            for group in ('scope', 'passband', 'full'):
                for plt in self.plts[group]:
                    plt.disableAutoRange(axis=pg.ViewBox.YAxis)
                    # plt.setYRange(-32, 32)
                    plt.setYRange(0, 32)
                    # yaxis.setTicks([[(x,"%d"%x) for x in range(-32,33,8)]])
                    plt.getAxis('left').setTicks([[(x,"%d"%x) for x in range(0,33,8)]])
        else:
            for group in ('scope', 'passband', 'full'):
                for plt in self.plts[group]:
                    plt.enableAutoRange()
                    plt.getAxis('left').setTicks(None)


    def init_plots(self):
        self.plts = {}
        self.lines = {}
        col = 0
        for group in ('scope', 'passband', 'full'):
            self.plts[group] = []
            self.lines[group] = []
            for row in range(4):
                plt = self.plotwin.addPlot(row, col)
                plt.getAxis('left').setWidth(50)
                plt.getAxis('left').setTickFont(self.tickfont)
                plt.getAxis('bottom').setTickFont(self.tickfont)
                plt.showGrid(y=True)
                self.plts[group].append(plt)
                line = plt.plot()
                self.lines[group].append(line)
            col += 1


    def yscale(self, data):
        return np.log2(np.fabs(data)+1) if self.yscale_type == 'logarithm' else data


    def plot_anim(self):
        row = 0
        for pol in ('A', 'B', 'C', 'D'):
            snap = self.fpga.snapshot_get('x8_vacc_scope_' + pol)
            self.scope[pol] = np.array(struct.unpack('>%di'%opts.nbins, snap['data']))
            # self.scope[pol][0] = 1  # Remove DC
            self.lines['scope'][row].setData(self.yscale(self.scope[pol]))
            # Borrow the loop to draw 2 other plot
            bram = self.fpga.read('x8_vacc_passband_' + pol, opts.nbins*4)
            self.passband[pol] = np.array(struct.unpack('>%di'%opts.nbins, bram))
            self.lines['passband'][row].setData(self.yscale(self.passband[pol]))
            self.lines['full'][row].setData(self.yscale(self.scope[pol] + self.passband[pol]))
            idx = np.argmax(self.scope[pol])
            print('%s:%4d %8d,%6d ' % (pol, idx, self.scope[pol][idx], np.mean(self.scope[pol]))),
            row += 1
        print('')


    def closeEvent(self, event):
        super(SBDWin, self).closeEvent(event)


    def on_config(self):
        print('<Configure> clicked')
        do_config(self.fpga)


    def on_capture(self):
        print('<Capture> clicked')
        # Stop timer to avoid re-entrant
        self.timer.stop()
        self.passband = self.scope.copy()
        for pol in ('A', 'B', 'C', 'D'):
            self.fpga.write('x8_vacc_passband_' + pol, struct.pack('>%di'%opts.nbins, *self.passband[pol]))
        # Restart animation timer
        self.timer.start()


    def on_clear(self):
        print('<Clear> clicked')
        # Stop timer to avoid re-entrant
        self.timer.stop()
        for pol in ('A', 'B', 'C', 'D'):
            #self.fpga.write('x8_vacc_passband_' + pol, struct.pack('>%di'%opts.nbins, *self.passband[pol]))
            self.fpga.write('x8_vacc_passband_' + pol, b'\0' * (opts.nbins*4))
        # Restart animation timer
        self.timer.start()


    def on_reset(self):
        print('<Reset> clicked')
        do_reset(self.fpga)


    def on_logarithm_yscale(self, checked):
        self.set_yscale_type('logarithm' if checked else 'linear')
        self.timer.stop()
        self.plot_anim()
        self.timer.start()

#class SBDWin


if __name__ == '__main__':

    try:

        lh = log_handlers.DebugLogHandler()
        logger = logging.getLogger(roach)
        logger.addHandler(lh)
        logger.setLevel(10)

        print('Connecting to server %s on port %i... ' % (roach, katcp_port)),
        fpga = katcp_wrapper.FpgaClient(roach, katcp_port, timeout=10, logger=logger)
        time.sleep(0.1)

        if fpga.is_connected():
            print('ok')
        else:
            print('ERROR connecting to server %s on port %i.\n' % (roach,katcp_port))
            exit_fail()

        parser = argparse.ArgumentParser()
        parser.add_argument('-s', '--skip', action='store_true', default=False, help='Skip programming FPGA')
        args = parser.parse_args()

        if not args.skip:
            print('Programming FPGA with  %s ... ' % bitstream),
            fpga.progdev(bitstream)
            print('done')

        app = QtGui.QApplication(sys.argv)
        mainwin = SBDWin(fpga)
        sys.exit(app.exec_())

    except KeyboardInterrupt:
        exit_clean()
    except Exception as e:
        exit_fail(e)
    finally:
        exit_clean()
