from astropy.coordinates import Angle
import astropy.units as u
from flask import Flask, request

from goetc.config import CONFIG, DATA
from goetc.simulation import Telescope, Camera, Sky, Simulation

app = Flask(__name__)


# init config
CONFIG.init()


def _coerce(value):
    """Convert numeric strings (e.g. from Vue's v-model) to numbers.

    Vue 2 sends <input type="number"> and <select> values as strings unless
    the .number modifier is used, so the backend must accept both.
    """
    if isinstance(value, dict):
        return {k: _coerce(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce(v) for v in value]
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return value
    return value


@app.route('/')
def hello_world():
    return app.send_static_file('index.html')


@app.route('/config')
def config():
    return {
        'bandpasses': CONFIG.recursive_groups(DATA.BANDPASS),
        'telescopes': CONFIG.groups(DATA.TELESCOPE),
        'cameras': CONFIG.groups(DATA.CAMERA),
        'qes': CONFIG.groups(DATA.QE),
        'templates': CONFIG.groups(DATA.SPECTRUM),
        'skies': CONFIG.groups(DATA.SKY)
    }


@app.route('/telescope/<string:name>')
def telescope(name):
    return CONFIG.telescope_config(name)


@app.route('/camera/<string:name>')
def camera(name):
    return CONFIG.camera_config(name)


@app.route('/sky/<string:name>')
def sky(name):
    return CONFIG.sky_config(name)


@app.route('/snr', methods=['POST'])
def signal_to_noise():
    # get config
    cfg = _coerce(request.get_json(silent=True) or {})

    # validate required parts
    required = ('telescope', 'camera', 'sky', 'target', 'sim')
    missing = [k for k in required if not isinstance(cfg.get(k), dict)]
    if not missing:
        for key in ('sim.bandpass', 'target.bandpass', 'target.template', 'target.magnitude'):
            section, field = key.split('.')
            if not isinstance(cfg[section].get(field), (int, float, str)):
                missing.append(key)
    if missing:
        return {'error': 'Missing parameter(s): %s.' % ', '.join(missing)}, 400

    # build objects
    telescope = Telescope(**cfg['telescope'])
    camera = Camera(**cfg['camera'])
    bandpass = CONFIG.bandpass(cfg['sim']['bandpass'])
    sky = Sky(**cfg['sky'])
    spec_bandpass = CONFIG.bandpass(cfg['target']['bandpass'])
    spectrum = CONFIG.spectrum(cfg['target']['template']).norm_to_mag(spec_bandpass, cfg['target']['magnitude'])

    # define parameters
    binning = int(cfg['sim'].get('binning', 1))
    aper_radius = Angle(cfg['sim'].get('aper_radius', 2.) * u.arcsec)
    exp_time = cfg['sim'].get('exp_time', 5.) * u.second

    # run sim
    sim = Simulation(telescope, camera, bandpass)
    sim.signal_to_noise(sky, spectrum, exp_time, aper_radius, binning)

    # return results
    return {
        'snr': sim.snr,
        'gain': camera.gain_binning(binning).value,
        'peak': sim.peak.value,
        'target': sim.target_counts.value,
        'dark': sim.dark_counts.value,
        'sky': sim.sky_counts.value
    }
