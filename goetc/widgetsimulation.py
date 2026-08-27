from typing import Optional
import astropy.units as u
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget
from astropy.coordinates import Angle

from .qt.widgetsimulation_ui import Ui_WidgetSimulation
from .simulation import Sky, Camera, Telescope, Simulation
from .config import CONFIG, DATA
from .spectrum import Spectrum, Bandpass


class WidgetSimulation(QWidget, Ui_WidgetSimulation):
    values_changed = pyqtSignal(Bandpass, float)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setupUi(self)

        self.sky: Optional[Sky] = None
        self.camera: Optional[Camera] = None
        self.telescope: Optional[Telescope] = None
        self.spectrum: Optional[Spectrum] = None
        self.filter: Optional[Bandpass] = None
        self.binning = 1

        # get all bandpasses
        self.comboFilter.addItems(CONFIG.recursive_groups(DATA.BANDPASS))

    @pyqtSlot(Telescope)
    def set_telescope(self, telescope: Telescope):
        self.telescope = telescope
        self.simulate()

    @pyqtSlot(Camera, int)
    def set_camera(self, camera: Camera, binning: int):
        self.camera = camera
        self.binning = binning
        self.simulate()

    @pyqtSlot(Spectrum)
    def set_spectrum(self, spectrum: Spectrum):
        self.spectrum = spectrum
        self.simulate()

    @pyqtSlot(Sky)
    def set_sky(self, sky: Sky):
        self.sky = sky
        self.simulate()

    def bandpass(self) -> Bandpass:
        return CONFIG.bandpass(self.comboFilter.currentText())

    @pyqtSlot(float, name='on_spinExpTime_valueChanged')
    @pyqtSlot(str, name='on_comboFilter_currentTextChanged')
    @pyqtSlot(float, name='on_spinAperRadius_valueChanged')
    def value_changed(self):
        self.values_changed.emit(self.bandpass(), self.spinExpTime.value())
        self.simulate()

    def simulate(self):
        # got everything?
        if self.sky is None or self.camera is None or self.telescope is None \
                or self.spectrum is None or isinstance(self.camera.qe, float):
            return

        # get exposure time, aperture radius and effective gain
        exp_time = self.spinExpTime.value()
        aper_radius = self.spinAperRadius.value()
        gain = self.camera.gain_binning(self.binning)

        # simulate
        sim = Simulation(self.telescope, self.camera, self.bandpass())
        sim.signal_to_noise(self.sky, self.spectrum, exp_time*u.second, Angle(aper_radius*u.arcsec), self.binning)

        # results
        self.spinSNR.setValue(sim.snr)
        self.lineSNR.setText(f'{sim.snr:.2f}')
        self.lineMagAcc.setText(f'{sim.mag_accuracy*1000.:.2f} mmag')

        # misc
        self.lineEffPixel.setText(f'{sim.eff_pixels*u.pix:.0f}')
        self.linePlateScale.setText(f'{sim.plate_scale/u.pix:.2f}')

        # aperture
        self.linePeakADU.setText(f'{sim.peak:.0f}')
        self.linePeakE.setText(f'{sim.peak * gain:0.2f}'.replace('electron', 'e-'))
        self.lineTargetADU.setText(f'{sim.target_counts:.0f}')
        self.lineTargetE.setText(f'{sim.target_counts * gain:0.2f}'.replace('electron', 'e-'))
        self.lineSkyADU.setText(f'{sim.sky_counts:.0f}')
        self.lineSkyE.setText(f'{sim.sky_counts * gain:0.2f}'.replace('electron', 'e-'))
        self.lineDarkADU.setText(f'{sim.dark_counts:.0f}')
        self.lineDarkE.setText(f'{sim.dark_counts * gain:0.2f}'.replace('electron', 'e-'))
        self.lineRONADU.setText(f'{sim.ron_counts:.0f}')
        self.lineRONE.setText(f'{sim.ron_counts * gain:0.2f}'.replace('electron', 'e-'))

        # S/N
        self.spinSNR.setValue(sim.snr)
