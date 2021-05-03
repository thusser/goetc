from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget
import astropy.units as u

from .qt.widgettelescope_ui import Ui_WidgetTelescope
from .config import CONFIG, DATA
from .simulation import Telescope


class WidgetTelescope(QWidget, Ui_WidgetTelescope):
    values_changed = pyqtSignal(Telescope)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setupUi(self)

        # currently updating values?
        self.updating = False

        # details checker
        self.widgetDetails.setVisible(False)
        self.checkDetails.stateChanged.connect(self.widgetDetails.setVisible)

        # add telescope presets and select first
        self.comboPreset.addItems([''] + CONFIG.groups(DATA.TELESCOPES))
        self.comboPreset.setCurrentIndex(1)

    @pyqtSlot(str, name='on_comboPreset_currentTextChanged')
    def on_preset_changed(self, name: str):
        # does telescope exist?
        if name not in CONFIG.groups(DATA.TELESCOPES):
            return
        
        # fill it
        self.updating = True
        telescope = CONFIG.telescope(name)
        self.spinAperture.setValue(telescope.aperture.to(u.meter).value)
        self.spinFratio.setValue(telescope.f_ratio)
        self.spinReflectivity.setValue(telescope.reflectivity)
        self.spinObscuration.setValue(telescope.obscuration)
        self.updating = False

        # update once
        self.value_changed()

    @pyqtSlot(float, name='on_spinAperture_valueChanged')
    @pyqtSlot(float, name='on_spinFratio_valueChanged')
    @pyqtSlot(float, name='on_spinReflectivity_valueChanged')
    @pyqtSlot(float, name='on_spinObscuration_valueChanged')
    def value_changed(self):
        # don't react if updating
        if self.updating:
            return

        # emit signal
        self.values_changed.emit(self.telescope())

    def telescope(self) -> Telescope:
        return Telescope(name=self.comboPreset.currentText(),
                         aperture=self.spinAperture.value(),
                         f_ratio=self.spinFratio.value(),
                         reflectivity=self.spinReflectivity.value(),
                         obscuration=self.spinObscuration.value())
