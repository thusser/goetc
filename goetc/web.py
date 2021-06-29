from astropy.coordinates import Angle
import astropy.units as u
from flask import Flask, request

from goetc.config import CONFIG, DATA
from goetc.simulation import Telescope, Camera, Sky, Simulation

app = Flask(__name__)


# init config
CONFIG.init()


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
        'templates': CONFIG.groups(DATA.SPECTRUM)
    }


@app.route('/telescope/<string:name>')
def telescope(name):
    return CONFIG.telescope_config(name)


@app.route('/camera/<string:name>')
def camera(name):
    return CONFIG.camera_config(name)


@app.route('/snr', methods=['POST'])
def signal_to_noise():
    # get config
    cfg = request.get_json(silent=True)

    # build objects
    telescope = Telescope(**cfg['telescope'])
    camera = Camera(**cfg['camera'])
    bandpass = CONFIG.bandpass(cfg['sim']['bandpass'])
    sky = Sky(**cfg['sky'])
    spec_bandpass = CONFIG.bandpass(cfg['target']['bandpass'])
    spectrum = CONFIG.spectrum(cfg['target']['template']).norm_to_mag(spec_bandpass, cfg['target']['magnitude'])

    # define parameters
    binning = cfg['sim']['binning']
    aper_radius = Angle(cfg['sim']['aper_radius'] * u.arcsec)
    exp_time = 5. * u.second

    # run sim
    sim = Simulation(telescope, camera, bandpass)
    sim.get_signal_to_noise(exp_time, spectrum, sky, aper_radius, binning)

    # return results
    return {
        'snr': sim.snr,
        'gain': camera.gain_binning(binning).value,
        'peak': sim.peak.value,
        'target': sim.target_counts.value,
        'dark': sim.dark_counts.value,
        'sky': sim.sky_counts.value
    }
