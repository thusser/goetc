"""Tests for the Flask web API."""

BASE = {
    'telescope': {'name': 'IAG50cm', 'aperture': 0.5148, 'focal_length': 3369,
                  'reflectivity': 81, 'obscuration': 2.49},
    'camera': {'name': 'SBIG STL-6303e', 'pixel_size': 9.0, 'readout_noise': 13,
               'dark_current': 0.02, 'gain': 1.4, 'bias': 1053, 'qe': 'KAF6303e'},
    'sky': {'name': 'Göttingen', 'magnitude': 19.0, 'seeing': 2.0,
            'airmass': 1.2, 'extinction': 0.25},
    'sim': {'bandpass': 'Bessel/V', 'aper_radius': 4, 'exp_time': 5.0, 'binning': 1},
    'target': {'template': 'G5 V', 'magnitude': 15.0, 'bandpass': 'Bessel/V'},
}


def post(client, payload):
    return client.post('/snr', json=payload)


def test_index_served(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'v-model.number' in r.data


def test_config_endpoint(client):
    cfg = client.get('/config').get_json()
    for key in ('bandpasses', 'telescopes', 'cameras', 'qes', 'templates', 'skies'):
        assert key in cfg
    assert 'SDSS/g' in cfg['bandpasses']
    assert 'Sutherland (SAAO)' in cfg['skies']


def test_telescope_endpoint(client):
    r = client.get('/telescope/IAG50cm')
    assert r.status_code == 200
    assert r.get_json()['aperture'] == 0.5148


def test_camera_endpoint(client):
    r = client.get('/camera/SBIG%20STL-6303e')
    assert r.status_code == 200
    assert r.get_json()['qe'] == 'KAF6303e'


def test_sky_endpoint(client):
    r = client.get('/sky/Sutherland%20(SAAO)')
    assert r.status_code == 200
    assert r.get_json()['magnitude'] == 21.8


def test_snr_numeric_payload(client):
    r = post(client, BASE)
    assert r.status_code == 200
    assert r.get_json()['snr'] > 0


def test_snr_string_payload(client):
    """Regression: the Vue frontend used to send strings (v-model)."""
    stringy = {k: ({kk: str(vv) for kk, vv in v.items()} if isinstance(v, dict) else v)
               for k, v in BASE.items()}
    r = post(client, stringy)
    assert r.status_code == 200
    assert r.get_json()['snr'] > 0


def test_snr_exp_time_honored(client):
    t5 = post(client, BASE).get_json()['snr']
    payload = dict(BASE, sim=dict(BASE['sim'], exp_time=10.0))
    t10 = post(client, payload).get_json()['snr']
    assert t10 > t5


def test_snr_binning_selects_gain(client):
    payload = dict(BASE)
    payload['camera'] = {'name': 'SBIG STL-6303e', 'pixel_size': 9.0, 'readout_noise': 13,
                         'dark_current': 0.02, 'gain': [1.4, 2.3, 2.3],
                         'bias': [1053, 675, 656], 'qe': 'KAF6303e'}
    payload['sim'] = dict(BASE['sim'], binning=2)
    r = post(client, payload)
    assert r.status_code == 200
    assert r.get_json()['gain'] == 2.3


def test_snr_constant_qe(client):
    payload = dict(BASE)
    payload['camera'] = dict(BASE['camera'], qe=0.5)
    r = post(client, payload)
    assert r.status_code == 200
    assert r.get_json()['snr'] > 0


def test_snr_with_optics_camera(client):
    payload = dict(BASE)
    payload['camera'] = {'name': 'FLI PL230', 'pixel_size': 18.0, 'gain': 1.85,
                         'readout_noise': 13, 'dark_current': 0.2,
                         'bias': [944, 1500, 2334], 'qe': 'E2V Broadband BI',
                         'optics': ['FLI Window F116']}
    r = post(client, payload)
    assert r.status_code == 200


def test_snr_missing_params_returns_400(client):
    r = post(client, {})
    assert r.status_code == 400
    bad = dict(BASE)
    del bad['target']
    assert post(client, bad).status_code == 400
    bad2 = dict(BASE)
    del bad2['sim']['bandpass']
    assert post(client, bad2).status_code == 400
