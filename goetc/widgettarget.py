from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget

from .qt.widgettarget_ui import Ui_WidgetTarget
from .spectrum import Spectrum, Bandpass
from .config import CONFIG, DATA


class WidgetTarget(QWidget, Ui_WidgetTarget):
    values_changed = pyqtSignal(Spectrum)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setupUi(self)

        # init updating
        self.updating = True

        # list spectra
        self.comboTemplate.addItems(CONFIG.groups(DATA.SPECTRUM))

        # list bandpasses
        self.comboFilter.addItems(CONFIG.recursive_groups(DATA.BANDPASS))

        # finished updating
        self.updating = False

    @pyqtSlot(str, name='on_comboTemplate_currentTextChanged')
    @pyqtSlot(float, name='on_spinBrightness_valueChanged')
    @pyqtSlot(str, name='on_comboFilter_currentTextChanged')
    def value_changed(self):
        # don't react if updating
        if self.updating:
            return

        # emit signal
        self.values_changed.emit(self.spectrum())

    def spectrum(self) -> Spectrum:
        # get spectrum
        spectrum = CONFIG.spectrum(self.comboTemplate.currentText())

        # scale
        return spectrum.norm_to_mag(self.bandpass(), self.spinBrightness.value())

    def bandpass(self) -> Bandpass:
        # get filter system and name
        return CONFIG.bandpass(self.comboFilter.currentText())
