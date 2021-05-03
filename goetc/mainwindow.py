import astropy.units as u
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QVBoxLayout, QSpacerItem, QSizePolicy, QScrollArea, QWidget
from astropy.coordinates import Angle
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from .config import CONFIG, DATA
from .simulation import Simulation
from .widgetcamera import WidgetCamera
from .widgetsimulation import WidgetSimulation
from .widgetsky import WidgetSky
from .widgettarget import WidgetTarget
from .widgettelescope import WidgetTelescope


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        QMainWindow.__init__(self, *args, **kwargs)

        # init config
        CONFIG.init(copy=False)

        # size
        self.resize(1200, 700)
        self.setWindowTitle('GoETC')

        # central widget
        self.centralWidget = QWidget()

        # set layout
        self.central_layout = QHBoxLayout(self.centralWidget)
        self.centralWidget.setLayout(self.central_layout)

        # add scroll area for settings
        self.scrollSettings = QScrollArea()
        self.scrollSettings.setWidgetResizable(True)
        self.scrollSettings.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scrollSettings.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollSettingsArea = QWidget()
        self.settings_layout = QVBoxLayout()
        self.scrollSettingsArea.setLayout(self.settings_layout)
        self.scrollSettings.setWidget(self.scrollSettingsArea)
        self.central_layout.addWidget(self.scrollSettings)

        # telescope
        self.widget_telescope = WidgetTelescope()
        self.settings_layout.addWidget(self.widget_telescope)

        # camera
        self.widget_camera = WidgetCamera()
        self.settings_layout.addWidget(self.widget_camera)

        # target
        self.widget_target = WidgetTarget()
        self.settings_layout.addWidget(self.widget_target)

        # sky
        self.widget_sky = WidgetSky()
        self.settings_layout.addWidget(self.widget_sky)

        # stretcher
        self.settings_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.settings_layout.setStretch(4, 2.)

        # plot
        self.figure = plt.Figure()
        self.ax = self.figure.add_subplot(111)
        self.ax2 = self.ax.twinx()
        self.canvas = FigureCanvas(self.figure)
        self.central_layout.addWidget(self.canvas)

        # simulation
        self.widget_simulation = WidgetSimulation()
        self.central_layout.addWidget(self.widget_simulation)
        self.widget_telescope.values_changed.connect(self.widget_simulation.set_telescope)
        self.widget_camera.values_changed.connect(self.widget_simulation.set_camera)
        self.widget_target.values_changed.connect(self.widget_simulation.set_spectrum)
        self.widget_sky.values_changed.connect(self.widget_simulation.set_sky)

        # fetch current values
        self.widget_simulation.telescope = self.widget_telescope.telescope()
        self.widget_simulation.camera = self.widget_camera.camera()
        self.widget_simulation.spectrum = self.widget_target.spectrum()
        self.widget_simulation.sky = self.widget_sky.sky()

        # finalize
        self.setCentralWidget(self.centralWidget)
        self.central_layout.setStretch(0, 0)
        self.central_layout.setStretch(1, 1)

        # signals that update plot
        for signal in [self.widget_target.values_changed,
                       self.widget_camera.values_changed,
                       self.widget_simulation.values_changed]:
            signal.connect(self.update_plot)

        # initial plot and simulation
        self.update_plot()
        self.widget_simulation.simulate()

    def update_plot(self):
        # create an axis
        self.ax.clear()
        self.ax2.clear()
        self.ax.set_xlim((200, 1200))

        # got spectrum?
        spectrum = self.widget_target.spectrum()
        if spectrum is not None:
            # plot spectrum
            self.ax.plot(spectrum.x, spectrum.y, 'k', label='Spectrum')

            # y lim
            s = spectrum.y[(spectrum.x >= 200 * u.nm) & (spectrum.x <= 1000 * u.nm)]
            self.ax.set_ylim((0, 1.1 * np.max(s).value))

            # label
            self.ax.set_xlabel(spectrum.x.unit)
            self.ax.set_ylabel(spectrum.y.unit)

        # plot filters
        bandpass = self.widget_simulation.bandpass()
        if bandpass is not None:
            self.ax2.plot(bandpass.x, bandpass.y, 'r', lw=1, label='Dest. bandpass')
        target_bandpass = self.widget_target.bandpass()
        if target_bandpass is not None:
            self.ax2.plot(target_bandpass.x, target_bandpass.y, 'b--', lw=1,
                          label='Target bandpass')

        # plot QE
        qe = self.widget_camera.camera().qe
        if qe is not None:
            self.ax2.plot(qe.x, qe.y, 'g', lw=1, label='QE')

        # finish drawing
        self.ax2.legend()
        self.canvas.draw()
