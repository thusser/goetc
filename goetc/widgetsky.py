from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget

from .qt.widgetsky_ui import Ui_WidgetSky
from .simulation import Sky
from .config import CONFIG, DATA


class WidgetSky(QWidget, Ui_WidgetSky):
    values_changed = pyqtSignal(Sky)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setupUi(self)

        # currently updating values?
        self.updating = True

        # add sky presets and select the home site by default
        self.comboPreset.addItems([''] + CONFIG.groups(DATA.SKY))
        if 'Göttingen' in CONFIG.groups(DATA.SKY):
            self.comboPreset.setCurrentText('Göttingen')
        else:
            self.comboPreset.setCurrentIndex(1)

        # finished updating
        self.updating = False

        # emit first value
        self.value_changed()

    @pyqtSlot(str, name='on_comboPreset_currentTextChanged')
    def on_preset_changed(self, name: str):
        # does preset exist?
        if name not in CONFIG.groups(DATA.SKY):
            return

        # fill it
        self.updating = True
        sky = CONFIG.sky(name)
        self.spinBrightness.setValue(sky.magnitude)
        self.spinSeeing.setValue(sky.seeing.value)
        self.spinAirmass.setValue(sky.airmass)
        self.spinExtinction.setValue(sky.extinction.value)
        self.updating = False

        # update once
        self.value_changed()

    @pyqtSlot(float, name='on_spinBrightness_valueChanged')
    @pyqtSlot(float, name='on_spinSeeing_valueChanged')
    @pyqtSlot(float, name='on_spinAirmass_valueChanged')
    @pyqtSlot(float, name='on_spinExtinction_valueChanged')
    def value_changed(self):
        # don't react if updating
        if self.updating:
            return

        # emit signal
        self.values_changed.emit(self.sky())

    def sky(self) -> Sky:
        return Sky(name=self.comboPreset.currentText(),
                   magnitude=self.spinBrightness.value(),
                   seeing=self.spinSeeing.value(),
                   airmass=self.spinAirmass.value(),
                   extinction=self.spinExtinction.value())
