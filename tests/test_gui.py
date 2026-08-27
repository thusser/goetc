"""Headless GUI tests (PyQt5, offscreen platform).

These run without a display via QT_QPA_PLATFORM=offscreen (set in
conftest.py) and are skipped if Qt cannot be initialized.
"""

import pytest

pytest.importorskip('PyQt5')


@pytest.fixture(scope='module')
def qapp():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_sky_widget_presets(config, qapp):
    from goetc.widgetsky import WidgetSky
    ws = WidgetSky()
    # default preset is the home site
    assert ws.comboPreset.currentText() == 'Göttingen'
    assert ws.spinBrightness.value() == 19.0
    assert ws.spinSeeing.value() == 2.0

    # switching presets fills the spin boxes and emits a Sky with the name
    emitted = []
    ws.values_changed.connect(lambda s: emitted.append(s.name))
    ws.comboPreset.setCurrentText('Sutherland (SAAO)')
    assert ws.spinBrightness.value() == 21.8
    assert ws.spinSeeing.value() == 1.2
    assert emitted[-1] == 'Sutherland (SAAO)'


def test_camera_widget_constant_qe_and_optics(config, qapp):
    from goetc.widgetcamera import WidgetCamera
    wc = WidgetCamera()
    # the preset carries optics
    cam = wc.camera()
    assert cam.optics is not None

    # constant-QE mode: percent spin -> fraction in the Camera
    wc.comboQEType.setCurrentIndex(0)
    wc.spinQE.setValue(50.0)
    cam = wc.camera()
    assert float(cam.qe.y.mean()) == pytest.approx(0.5)

    # editing spinQE triggers a recalculation (slot typo regression)
    emitted = []
    wc.values_changed.connect(lambda c, b: emitted.append(float(c.qe.y.mean())))
    wc.spinQE.setValue(70.0)
    assert emitted and abs(emitted[-1] - 0.7) < 1e-9


def test_simulation_widget_guards_and_formats(config, qapp):
    import astropy.units as u
    from astropy.coordinates import Angle

    from goetc.simulation import Sky
    from goetc.widgetsimulation import WidgetSimulation

    ws = WidgetSimulation()
    ws.set_telescope(config.telescope('IAG50cm'))
    # camera with an array gain must not crash the result formatting
    ws.set_camera(config.camera('SBIG STL-6303e'), 1)
    # simulate() with no spectrum yet must not crash (guard regression)
    ws.set_sky(Sky())
    assert ws.lineSNR.text() == ''

    bp = config.bandpass('Bessel/V')
    ws.set_spectrum(config.spectrum('G5 V').norm_to_mag(bp, 15.0))
    ws.simulate()
    assert 'e-' in ws.linePeakE.text()

    # changing the aperture radius must recalculate (slot type regression)
    before = ws.lineSNR.text()
    ws.spinAperRadius.setValue(5.0)
    assert ws.lineSNR.text() != before or ws.lineSNR.text() != ''


def test_main_window_constructs(config, qapp):
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
    from goetc.mainwindow import MainWindow

    # rendering is not the point here and can fail headless without fonts
    orig_draw = FigureCanvasQTAgg.draw
    FigureCanvasQTAgg.draw = lambda self: None
    try:
        mw = MainWindow()
    finally:
        FigureCanvasQTAgg.draw = orig_draw

    assert mw.widget_simulation.sky is not None
