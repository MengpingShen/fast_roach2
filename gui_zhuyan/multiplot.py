'''	Multiple plot groups layout
'''

from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import pyqtgraph as pg

view_rows = 2
view_cols = 2
plot_rows = 3
view_cols = 2

app = QtGui.QApplication([])
view = pg.GraphicsView()
layout = pg.GraphicsLayout(border=(100,100,100))
view.setCentralItem(layout)
view.show()
view.setWindowTitle('AAAAA')
view.resize(1600,1200)
