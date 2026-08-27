"""Tests for the simulation physics (Telescope, Camera, Sky, Simulation)."""

import copy

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import Angle

from conftest import run_sim
from goetc.simulation import Camera, Sky, mag2flux


def test_mag2flux():
    assert mag2flux(0.0 * u.mag) == pytest.approx(1.0)
    assert mag2flux(1.0 * u.mag) == pytest.approx(10 ** -0.4)


def test_telescope_plate_scale(config):
    tel = config.telescope('IAG50cm')
    assert tel.plate_scale.value > 0


def test_camera_binning_selection(config):
    cam = config.camera('SBIG STL-6303e')  # gain/bias are lists
    assert cam.gain_binning(1).value == pytest.approx(1.4)
    assert cam.gain_binning(2).value == pytest.approx(2.3)
    assert cam.bias_binning(1).value == pytest.approx(1053)
    assert cam.bias_binning(3).value == pytest.approx(656)


def test_camera_scalar_gain_binning():
    cam = Camera(name='x', pixel_size=9.0, gain=1.4, readout_noise=13,
                 dark_current=0.02, bias=1053, qe='KAF6303e')
    assert cam.gain_binning(1).value == pytest.approx(1.4)
    assert cam.gain_binning(2).value == pytest.approx(1.4)


def test_camera_optics_resolved(config):
    cam = config.camera('FLI PL230')
    assert cam.optics is not None
    assert len(cam.optics) == 1


def test_camera_without_optics_has_none(config):
    cam = config.camera('SBIG STL-6303e')
    assert cam.optics is None


def test_sky_construction():
    sky = Sky(magnitude=21.0, seeing=1.5, airmass=1.3, extinction=0.1, name='Test')
    assert sky.name == 'Test'
    assert sky.seeing.unit == u.arcsec
    assert sky.extinction.unit == u.mag


def test_signal_to_noise_runs_and_positive(sim_objects):
    sim = run_sim(sim_objects)
    assert sim.snr > 0
    assert sim.peak.value > 0
    assert sim.target_counts.value > 0
    assert sim.sky_counts.value > 0
    assert sim.mag_accuracy > 0


def test_snr_scales_with_sqrt_exposure_time(sim_objects):
    t5 = run_sim(sim_objects)
    objs10 = copy.deepcopy(sim_objects)
    objs10['exp_time'] = 10. * u.second
    t10 = run_sim(objs10)
    ratio = t10.snr / t5.snr
    # between sqrt(2) (photon-noise dominated) and 2 (read-noise dominated)
    assert 2 ** 0.5 - 0.05 <= ratio <= 2.0 + 0.05


def test_snr_improves_with_darker_sky(sim_objects):
    dark = dict(sim_objects, sky=Sky(magnitude=22.0, seeing=1.0, airmass=1.2, extinction=0.1))
    bright = dict(sim_objects, sky=Sky(magnitude=19.0, seeing=1.0, airmass=1.2, extinction=0.1))
    assert run_sim(dark).snr > run_sim(bright).snr


def test_snr_worsens_with_worse_seeing(sim_objects):
    good = dict(sim_objects, sky=Sky(magnitude=21.0, seeing=1.0, airmass=1.2, extinction=0.1))
    bad = dict(sim_objects, sky=Sky(magnitude=21.0, seeing=3.0, airmass=1.2, extinction=0.1))
    assert run_sim(good).snr > run_sim(bad).snr


def test_optics_reduce_snr(sim_objects, config):
    objs = copy.deepcopy(sim_objects)
    objs['camera'] = config.camera('FLI PL230')
    with_optics = run_sim(objs)
    objs['camera'] = Camera(name='FLI PL230 no optics', pixel_size=18.0, gain=1.85,
                            readout_noise=13, dark_current=0.2, qe='E2V Broadband BI',
                            bias=[944, 1500, 2334])
    without_optics = run_sim(objs)
    assert with_optics.snr < without_optics.snr


def test_constant_qe_simulates(sim_objects):
    objs = dict(sim_objects)
    objs['camera'] = Camera(name='c', pixel_size=9.0, gain=1.4, readout_noise=13,
                            dark_current=0.02, bias=1053, qe=0.5)
    assert run_sim(objs).snr > 0


def test_sky_presets_produce_expected_ordering(config):
    import astropy.units as u
    from astropy.coordinates import Angle

    bp = config.bandpass('Bessel/V')
    spec = config.spectrum('G5 III').norm_to_mag(bp, 15.0)
    base = {
        'telescope': config.telescope('IAG50cm'),
        'camera': config.camera('SBIG STL-6303e'),
        'bandpass': bp,
        'spectrum': spec,
        'exp_time': 5. * u.second,
        'aper_radius': Angle(2.0 * u.arcsec),
        'binning': 1,
    }
    snrs = {name: run_sim(dict(base, sky=config.sky(name))).snr
            for name in ('Göttingen', 'Sutherland (SAAO)', 'McDonald Observatory')}
    # darker sites give better S/N
    assert snrs['Sutherland (SAAO)'] > snrs['McDonald Observatory'] > snrs['Göttingen']
