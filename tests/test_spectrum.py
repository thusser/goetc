"""Tests for spectrum handling (XYData, Spectrum, QE, Bandpass)."""

import astropy.units as u
import numpy as np
import pytest

from goetc.spectrum import Bandpass, QE, Spectrum, XYData


def test_xydata_loads_with_units():
    d = XYData(x=np.arange(10) * u.nm, y=np.arange(10) * u.ct)
    assert d.x.unit == u.nm
    assert d.y.unit == u.ct


def test_xydata_resample():
    x = np.array([0., 1., 2., 3.]) * u.nm
    y = np.array([0., 1., 2., 3.]) * u.ct
    d = XYData(x=x, y=y)
    out = d.resample(XYData(x=np.array([0.5, 2.5]) * u.nm, y=np.zeros(2) * u.ct))
    assert out.y[0] == pytest.approx(0.5)
    assert out.y[1] == pytest.approx(2.5)


def test_xydata_resample_outside_range_is_zero():
    d = XYData(x=np.array([1., 2., 3.]) * u.nm, y=np.array([1., 1., 1.]) * u.ct)
    out = d.resample(XYData(x=np.array([0., 4.]) * u.nm, y=np.zeros(2) * u.ct))
    assert out.y[0] == 0
    assert out.y[1] == 0


def test_norm_area_integrates_to_one():
    x = np.linspace(0, 10, 100) * u.nm
    y = np.ones(100) * u.ct
    d = XYData(x=x, y=y).norm_area()
    area = float(np.trapezoid(d.y, d.x))
    assert area == pytest.approx(1.0)


def test_spectrum_norm_to_mag(config):
    bp = config.bandpass('Bessel/V')
    spec = config.spectrum('G5 III').norm_to_mag(bp, 15.0)
    assert float(bp.mag(spec)) == pytest.approx(15.0, abs=1e-6)


def test_qe_percent_to_fraction(config):
    qe = config.sensor('KAF6303e')
    assert qe.y.max() <= 1.0
    assert qe.y.min() >= 0.0


def test_qe_apply_reduces_flux(config):
    spec = config.spectrum('G5 III')
    qe = config.sensor('KAF6303e')
    applied = qe.apply(spec)
    assert (applied.y <= spec.y).all()


def test_bandpass_vega_magnitude(config):
    # Vega's V magnitude is ~0.03 by definition of the Vega system
    bp = config.bandpass('Bessel/V')
    vega = config.vega_spectrum()
    assert float(bp.mag(vega)) == pytest.approx(0.03, abs=0.05)


def test_bandpass_apply_outside_range_is_zero(config):
    bp = config.bandpass('Bessel/V')
    spec = config.spectrum('G5 III')
    applied = bp.apply(spec)
    # wavelengths far outside the V filter must contribute nothing
    far = spec.x < 400 * u.nm
    assert (applied.y[far] == 0).all()


def test_bandpass_integrate(config):
    bp = config.bandpass('Bessel/V')
    spec = config.spectrum('G5 III')
    assert bp.integrate(spec) > 0


def test_constant_qe_is_flat(config):
    from goetc.simulation import Camera
    cam = Camera(name='x', pixel_size=9.0, gain=1.4, readout_noise=13,
                 dark_current=0.02, bias=1053, qe=0.5)
    assert isinstance(cam.qe, QE)
    assert float(cam.qe.y.mean()) == pytest.approx(0.5)
