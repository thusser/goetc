from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget
import astropy.units as u

from .qt.widgetcamera_ui import Ui_WidgetCamera
from .config import CONFIG, DATA, PROFILE
from .simulation import Camera


class WidgetCamera(QWidget, Ui_WidgetCamera):
    values_changed = pyqtSignal(Camera, int)
    
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setupUi(self)

        # currently updating values?
        self.updating = True

        # details checker
        self.widgetDetails.setVisible(False)
        self.checkDetails.stateChanged.connect(self.widgetDetails.setVisible)

        # QE
        self.comboSensor.addItems(CONFIG.group_entries(DATA.PROFILE, PROFILE.QE))
        self.comboQEType.currentIndexChanged.connect(self.stackedQE.setCurrentIndex)

        # add telescope presets and select first
        self.comboPreset.addItems([''] + CONFIG.groups(DATA.CAMERA))
        self.comboPreset.setCurrentIndex(1)

        # finished updating
        self.updating = False

    @pyqtSlot(str, name='on_comboPreset_currentTextChanged')
    @pyqtSlot(int, name='on_spinBinning_valueChanged')
    def on_preset_changed(self):
        # get preset and binning
        preset = self.comboPreset.currentText()
        binning = self.spinBinning.value()

        # does camera exist?
        if preset not in CONFIG.groups(DATA.CAMERA):
            return

        # fill it
        self.updating = True
        camera = CONFIG.camera(preset)
        self.spinPixelSize.setValue(camera.pixel_size.to(u.micron).value)
        self.spinRON.setValue(camera.readout_noise.value)
        self.spinDark.setValue(camera.dark_current.value)
        self.spinGain.setValue(camera.gain[binning - 1].value)
        self.spinBias.setValue(camera.bias[binning - 1].value)
        if isinstance(camera.qe, float):
            self.comboQEType.setCurrentIndex(0)
            self.spinQE.setValue(camera.qe)
        else:
            self.comboQEType.setCurrentIndex(1)
            self.comboSensor.setCurrentText(camera.qe_name)
        self.updating = False

        # update once
        self.value_changed()

    @pyqtSlot(float, name='on_spinPixelSize_valueChanged')
    @pyqtSlot(float, name='on_spinRON_valueChanged')
    @pyqtSlot(float, name='on_spinDark_valueChanged')
    @pyqtSlot(float, name='on__valueChanged')
    @pyqtSlot(float, name='on_spinGain_valueChanged')
    @pyqtSlot(float, name='on_spinBias_valueChanged')
    def value_changed(self):
        # don't react if updating
        if self.updating:
            return

        # emit signal
        self.values_changed.emit(self.camera(), self.binning())

    def camera(self) -> Camera:
        if self.comboQEType.currentIndex() == 0:
            qe = self.spinCameraQE.value()
        else:
            qe = CONFIG.sensor(self.comboSensor.currentText())

        return Camera(name=self.comboPreset.currentText(),
                      pixel_size=self.spinPixelSize.value(),
                      gain=self.spinGain.value(),
                      readout_noise=self.spinRON.value(),
                      dark_current=self.spinDark.value(),
                      bias=self.spinBias.value(),
                      qe=qe)

    def binning(self):
        return self.spinBinning.value()
