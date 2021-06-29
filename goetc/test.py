"""
Test program for running GoETC in a script.
"""

import astropy.units as u
from astropy.coordinates import Angle
from goetc.simulation import Simulation, Sky
from goetc.config import CONFIG

# init configuration
CONFIG.init()

# define parameters
binning = 1
aper_radius = Angle(2.0 * u.arcsec)
magn = 15.0 * u.mag
exp_time = 5. * u.second

# spectrum
spec_bandpass = CONFIG.bandpass('Bessel/V')
spectrum = CONFIG.spectrum('G5 III').norm_to_mag(spec_bandpass, magn)

# get telescope/camera/bandpass/sky
telescope = CONFIG.telescope('IAG50cm')
camera = CONFIG.camera('SBIG STL-6303e')
bandpass = CONFIG.bandpass('Bessel/V')
sky = Sky()

# get simulation
sim = Simulation(telescope, camera, bandpass)

print ('\nS/N test:')
print ('input:',exp_time)
sim.get_signal_to_noise(exp_time, spectrum, sky, aper_radius, binning)
print('magnitude:',sim.magnitude)
print('exposure time:',sim.exp_time)
print('S/N:', sim.snr)
print('peak count:', sim.peak)

print ('\nexposure time test:')
snr = sim.snr
print ('input:',snr)
sim.get_exposure_time (snr, spectrum, sky, aper_radius, binning)
print('magnitude:',sim.magnitude)
print('exposure time:',sim.exp_time)
print('S/N:', sim.snr)
print('peak count:', sim.peak)

print ('\nmagnitude test:')
snr = sim.snr
exptime = sim.exp_time
print ('input:',snr,exptime)
sim.get_magnitude (snr, exp_time, spectrum, sky, aper_radius, binning)
print('magnitude:',sim.magnitude)
print('exposure time:',sim.exp_time)
print('S/N:', sim.snr)
print('peak count:', sim.peak)
