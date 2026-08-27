"""Tests that every data file in the package loads and is well-formed."""

import astropy.units as u
import pytest

from goetc.config import DATA


def test_all_cameras_construct(config):
    for name in config.groups(DATA.CAMERA):
        cam = config.camera(name)
        assert cam.pixel_size.value > 0
        assert cam.qe is not None


def test_all_telescopes_construct(config):
    for name in config.groups(DATA.TELESCOPE):
        tel = config.telescope(name)
        assert tel.aperture.value > 0
        assert tel.focal_length.value > 0


def test_all_spectra_load(config):
    for name in config.groups(DATA.SPECTRUM):
        spec = config.spectrum(name)
        assert len(spec.x) > 10
        assert (spec.x[1:] > spec.x[:-1]).all()


def test_all_bandpasses_load(config):
    for entry in config.recursive_groups(DATA.BANDPASS):
        bp = config.bandpass(entry)
        assert len(bp.x) > 2
        assert (bp.x[1:] > bp.x[:-1]).all()
        assert bp.y.min() >= 0


def test_all_qes_load(config):
    for name in config.groups(DATA.QE):
        qe = config.sensor(name)
        assert (qe.x[1:] > qe.x[:-1]).all()
        assert 0.0 <= qe.y.min() and qe.y.max() <= 1.0


def test_all_optics_load(config):
    for name in config.groups(DATA.OPTICS):
        opt = config.optics(name)
        assert (opt.x[1:] >= opt.x[:-1]).all()
        assert 0.0 <= opt.y.min() and opt.y.max() <= 1.0


def test_all_sky_presets_load(config):
    for name in config.groups(DATA.SKY):
        sky = config.sky(name)
        assert sky.magnitude > 0
        assert sky.seeing.value > 0
        assert sky.airmass > 0
        assert sky.extinction.value > 0


def test_spectra_cover_visible_range(config):
    # the science use case needs at least the optical range
    for name in config.groups(DATA.SPECTRUM):
        spec = config.spectrum(name)
        assert spec.x.min() < 400 * u.nm
        assert spec.x.max() > 800 * u.nm
