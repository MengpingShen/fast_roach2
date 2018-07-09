
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

app = QtGui.QApplication([])
from pyqtgraph.parametertree import Parameter, ParameterTree


defparams = [
    {'name': 'Target board', 'type': 'group', 'children': [
        {'name': 'roach_name',  'type': 'str',	'value': 'roach7'},
        {'name': 'katcp_port',  'type': 'int',	'value': '7147'},
        {'name': 'bitstream',   'type': 'list',	'values': [], 'value': 0}
    ]},
    {'name': 'Gateware parameters', 'type': 'group', 'children': [
        {'name': 'fft_shift',   'type': 'str',  'value': '2**32-1'},
        {'name': 'gain',        'type': 'str',  'value': '0x1000'},
        {'name': 'acc_len',     'type': 'int',  'value': 1023},
        {'name': 'bit_select',  'type': 'list', 'values': [0,1,2,3], 'value': 1},
        {'name': 'fabric_ip',   'type': 'str',  'value': '10.0.1.227'},
        {'name': 'fabric_port', 'type': 'int',  'value': 33333},
        {'name': 'host_ip',     'type': 'str',  'value': '10.0.1.127'},
        {'name': 'host_port',   'type': 'int',  'value': 12345},
        {'name': 'use_tvg',     'type': 'bool', 'value': True},
    ]}
]

p = Parameter.create(name='params', type='group', children=defparams)

t = ParameterTree()
t.setParameters(p, showTop=False)
t.setWindowTitle('Parameter Tree')

def programFPGA():
    print('Program FPGA')

def setParam():
    print('Set Param')


btnProgram = QtGui.QPushButton('Program FPGA')
btnProgram.clicked.connect(programFPGA)
btnSetParam = QtGui.QPushButton('Config parameters')
btnSetParam.clicked.connect(setParam)

win = QtGui.QWidget()
layout = QtGui.QGridLayout()
win.setLayout(layout)
layout.addWidget(QtGui.QLabel("These are two views of the same data."), 0,  0, 1, 2)
layout.addWidget(t, 1, 0, 1, 2)
layout.addWidget(btnProgram, 2, 0)
layout.addWidget(btnSetParam, 2, 1)
win.show()
win.resize(300,450)


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    QtGui.QApplication.instance().exec_()
#    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
#        QtGui.QApplication.instance().exec_()
