"""Shared fixtures for the GoETC test suite.

The tests run against the real package data (goetc/data), since that data
is part of the product. PyQt5-based widget tests run headless via the
``offscreen`` platform and are skipped when Qt is not available.
"""

import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture(scope='session')
def config():
    """The global CONFIG singleton, initialized once per session."""
    from goetc.config import CONFIG
    CONFIG.init()
    return CONFIG


@pytest.fixture(scope='session')
def client():
    """Flask test client for the web app."""
    from goetc.web import app
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture()
def sim_objects(config):
    """A standard telescope/camera/bandpass/spectrum/sky combination."""
    import astropy.units as u
    from astropy.coordinates import Angle

    bandpass = config.bandpass('Bessel/V')
    spectrum = config.spectrum('G5 III').norm_to_mag(bandpass, 15.0)
    return {
        'telescope': config.telescope('IAG50cm'),
        'camera': config.camera('SBIG STL-6303e'),
        'bandpass': bandpass,
        'spectrum': spectrum,
        'sky': config.sky('Göttingen'),
        'exp_time': 5. * u.second,
        'aper_radius': Angle(2.0 * u.arcsec),
        'binning': 1,
    }


def run_sim(objs):
    """Run the signal-to-noise simulation for a sim_objects dict."""
    from goetc.simulation import Simulation
    sim = Simulation(objs['telescope'], objs['camera'], objs['bandpass'])
    sim.signal_to_noise(objs['sky'], objs['spectrum'], objs['exp_time'],
                        objs['aper_radius'], objs['binning'])
    return sim
