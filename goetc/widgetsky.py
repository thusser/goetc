from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget

from .qt.widgetsky_ui import Ui_WidgetSky
from .simulation import Sky


class WidgetSky(QWidget, Ui_WidgetSky):
    values_changed = pyqtSignal(Sky)

    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setupUi(self)

        # currently updating values?
        self.updating = False

        # emit first value
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
        return Sky(magnitude=self.spinBrightness.value(),
                   seeing=self.spinSeeing.value(),
                   airmass=self.spinAirmass.value(),
                   extinction=self.spinExtinction.value())
