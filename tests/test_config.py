"""Tests for the configuration system and data loaders."""

import os

import pytest

from goetc.config import DATA


def test_init_loads_all_categories(config):
    for category in (DATA.TELESCOPE, DATA.CAMERA, DATA.QE, DATA.OPTICS,
                     DATA.BANDPASS, DATA.SPECTRUM, DATA.SKY):
        assert len(config.config[category]) > 0, category


def test_bandpass_groups(config):
    groups = config.recursive_groups(DATA.BANDPASS)
    assert 'Bessel/V' in groups
    assert 'SDSS/g' in groups
    assert 'Baader/R' in groups
    assert 'TESS/TESS' in groups


def test_camera_loader(config):
    cam = config.camera('SBIG STL-6303e')
    assert cam.name == 'SBIG STL-6303e'
    assert cam.qe_name == 'KAF6303e'


def test_telescope_loader(config):
    tel = config.telescope('IAG50cm')
    assert tel.name == 'IAG50cm'
    assert tel.aperture.value > 0


def test_spectrum_loader(config):
    spec = config.spectrum('G5 III')
    assert len(spec.x) > 0


def test_sky_loader(config):
    for name in ('Göttingen', 'Sutherland (SAAO)', 'McDonald Observatory'):
        sky = config.sky(name)
        assert sky.name == name
        assert sky.magnitude > 0
        assert sky.seeing.value > 0


def test_sensor_loader(config):
    qe = config.sensor('KAF6303e')
    # QE is stored in percent and divided by 100 on load
    assert qe.y.max() <= 1.0


def test_optics_loader(config):
    opt = config.optics('FLI Window F116')
    # vendor files are not sorted; loader must return ascending wavelength
    assert (opt.x[1:] >= opt.x[:-1]).all()
    assert opt.y.max() <= 1.0


def test_unknown_name_raises(config):
    with pytest.raises(ValueError):
        config.camera('No Such Camera')
    with pytest.raises(ValueError):
        config.sky('No Such Sky')


def test_init_copy_true(tmp_path, monkeypatch):
    """CONFIG.init(copy=True) must copy the data into a user config dir."""
    from goetc.config import Config
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.delenv('APPDATA', raising=False)
    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)

    cfg = Config()
    cfg.init(copy=True)

    assert os.path.exists(cfg._path)
    # a top-level file and the subdirectories must have been copied
    assert os.path.exists(os.path.join(cfg._path, 'alpha_lyr_stis_010.csv'))
    assert len(cfg.config[DATA.CAMERA]) == 3
    assert 'SDSS/g' in cfg.recursive_groups(DATA.BANDPASS)
