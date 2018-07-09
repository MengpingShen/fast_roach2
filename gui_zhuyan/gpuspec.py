
import sys
import numpy as np
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg


nlogbins = 22
nbins = 1 << nlogbins


class GPUSpecWin(QtGui.QWidget):

    def __init__(self):
        super(GPUSpecWin, self).__init__()
        self.init_widgets()
        self.init_plots()
        self.setGeometry(200, 200, 1024, 768)
        self.setWindowTitle('GPUSpecWin')
        self.show()

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

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hb1)
        vbox.addLayout(hb2)
        vbox.addLayout(hb3)
        vbox.addStretch(1)

        self.plotwin = pg.GraphicsLayoutWidget()

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.plotwin)
        hbox.addLayout(vbox)

        self.setLayout(hbox)

    def init_plots(self):
        self.plt = []
        self.plt.append(self.plotwin.addPlot(title="AA").plot())
        self.plt.append(self.plotwin.addPlot(title="BB").plot())
        self.plotwin.nextRow()
        self.plt.append(self.plotwin.addPlot(title="Re(AB*)").plot())
        self.plt.append(self.plotwin.addPlot(title="Im(AB*)").plot())

        self.proc = QtCore.QProcess();
        self.proc.readyReadStandardOutput.connect(self.data_avail)
        self.proc.readyReadStandardError.connect(self.prompt_avail)
        # self.proc.start('python blkout.py %d' % (nbins * 4))
        self.proc.start('./gpuspec 4 22 250 50 10.0.5.127:12345 10.0.6.127:12345 10.0.7.127:12345 10.0.8.127:12345')

    def data_avail(self):
        global nbins

        nbytes = self.proc.bytesAvailable()
        blklen = nbins * 4 * 4
        if nbytes < blklen:
            return
        # print(nbins, blklen, nbytes)
        data = np.frombuffer(self.proc.read(blklen), dtype=np.float32).reshape((4, -1, 1024), order='F')
        nbytes = self.proc.bytesAvailable()
        # print(nbytes)
        # downsamp = data.max(axis=1)
        dmax = data.max(axis=1)
        dmin = data.min(axis=1)
        downsamp = np.where(np.fabs(dmax) > np.fabs(dmin), dmax, dmin )
        for i in range(4):
            self.plt[i].setData(downsamp[i, :])

    def prompt_avail(self):
        sys.stdout.write(self.proc.readAllStandardError())

    def closeEvent(self, event):
        self.proc.kill()
        self.proc.waitForFinished()
        super(GPUSpecWin, self).closeEvent(event)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    gpuspec = GPUSpecWin()
    sys.exit(app.exec_())
