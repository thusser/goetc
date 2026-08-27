import math
from typing import List, Union
import astropy.units as u
import numpy as np
import scipy
from astropy import constants as const
from astropy.coordinates import Angle
from astropy.units import Quantity

import goetc
from goetc.spectrum import XYData, QE, Bandpass, Spectrum, trapz


def data_path():
    return goetc.data_path()


def mag2flux(mag: u.mag, flux0=1.):
    return flux0 * 10.**(-0.4 * mag.value)


def c(value, unit, float_unit=None):
    # if no float type is given, it's the same as unit
    if float_unit is None:
        float_unit = unit

    # if float is given, assign unit
    if not isinstance(value, Quantity):
        value = value * float_unit

    # return final unit
    return value.to(unit)


class Telescope:
    def __init__(self, name: str, aperture: float, focal_length: float, reflectivity: float, obscuration: float):
        # set it
        self.name = name
        self.aperture = c(aperture, u.meter)
        self.focal_length = c(focal_length, u.m, float_unit=u.mm)
        self.plate_scale = (1. * u.radian / self.focal_length).to(u.arcsec/u.m)
        self.reflectivity = reflectivity / 100.
        self.obscuration = obscuration / 100.

    def effective_area(self):
        return math.pi * self.aperture**2 * (1. - self.obscuration) * self.reflectivity


class Camera:
    def __init__(self, name: str, pixel_size: float, gain: Union[float, List[float]], readout_noise: float,
                 dark_current: float, qe: Union[float, XYData, str], bias: Union[float, List[float]],
                 optics: List[Union[str, XYData]] = None):
        # set it
        self.name = name
        self.pixel_size = c(pixel_size, u.meter, float_unit=u.micron)
        self.gain = c(gain, u.electron/u.adu)
        self.readout_noise = c(readout_noise, u.adu)
        self.dark_current = c(dark_current, u.adu/u.second)
        self.bias = c(bias, u.adu)
        self.qe_name = None

        # QE given as a name?
        if isinstance(qe, str):
            from .config import CONFIG
            self.qe_name = qe
            self.qe = CONFIG.sensor(qe)
        # constant QE -> flat response curve over the standard range
        elif isinstance(qe, (int, float)):
            lam = np.arange(300, 1101) * u.nm
            self.qe = QE(x=lam, y=np.full(lam.shape, float(qe) * 100.))
        else:
            self.qe = qe

        # resolve optics names to transmission curves
        from .config import CONFIG
        self.optics = None
        if optics:
            self.optics = [CONFIG.optics(o) if isinstance(o, str) else o for o in optics]

    def apply_throughput(self, spec: Spectrum) -> Spectrum:
        """Apply the QE and all optics transmission curves to a spectrum."""
        out = self.qe.apply(spec)
        for opt in self.optics or []:
            t = opt.resample(spec.data)
            out = Spectrum(x=out.x, y=out.y * t.y)
        return out

    def bias_binning(self, binning: int):
        try:
            return self.bias[binning - 1]
        except TypeError:
            return self.bias

    def gain_binning(self, binning: int):
        try:
            return self.gain[binning - 1]
        except TypeError:
            return self.gain


class Sky:
    def __init__(self, magnitude: float = 22.0, seeing: float = 1.0, airmass: float = 2.0,
                 extinction: float = 0.2):
        """
        Args:
            magnitude: Surface brightness of the sky in mag/arcsec^2, in the
                same filter as the simulation.
            seeing: Seeing in arcsec.
            airmass: Airmass.
            extinction: Atmospheric extinction in mag/airmass.
        """

        # store
        self.magnitude = magnitude
        self.seeing = Angle(c(seeing, u.arcsec))
        self.airmass = airmass
        self.extinction = c(extinction, u.mag)


class Simulation:
    def __init__(self, telescope: Telescope, camera: Camera, bandpass: Bandpass):
        """
        Args:
            telescope: Telescope to use.
            camera: Camera to use.
            bandpass: Bandpass (filter) of the simulation.
        """

        # store
        self.telescope = telescope
        self.camera = camera
        self.filter = bandpass

        # results
        self.target_counts = 0
        self.sky_counts = 0
        self.dark_counts = 0
        self.ron_counts = 0
        self.eff_pixels = 0
        self.plate_scale = 0
        self.snr = 0
        self.mag_accuracy = 0
        self.peak = 0

    def signal_to_noise(self, sky: Sky, target: Spectrum, exp_time: float, aper_radius: Angle, binning: int):
        from goetc.config import CONFIG

        # gain and bias
        gain = self.camera.gain_binning(binning)
        bias = self.camera.bias_binning(binning)

        # apply QE, optics and filter to target spectrum
        target = self.filter.apply(self.camera.apply_throughput(target))

        # same for sky, but we just get the flux of vega, scaled to sky brightness and to 1 arcsec^2
        vega = CONFIG.vega_spectrum().norm_to_mag(self.filter, sky.magnitude)
        sky_spec = self.filter.apply(self.camera.apply_throughput(vega))
        sky_spec.data.y *= self.solid_angle_of_aperture(aper_radius) / (1. * u.arcsec).to(u.radian)**2

        # extinction: the target magnitude is a catalogue (extraterrestrial)
        # value, so it is attenuated by the atmosphere. The sky brightness is
        # assumed to be the observed surface brightness at the given airmass,
        # so it is *not* attenuated here.
        extinct = mag2flux(sky.extinction * sky.airmass)
        target.data.y *= extinct

        # effective aperture and plate scale
        self.eff_pixels = self.pixels_in_aperture(aper_radius, sky.seeing, binning)
        self.plate_scale = self.arcsec_per_pixel(binning)

        # calculate fraction of total in aperture
        fwhm = sky.seeing / self.plate_scale
        sig2 = fwhm**2 / (8. * math.log(2))
        rpix = aper_radius / self.plate_scale
        fract = 1. - np.exp(-0.5 * rpix**2 / sig2)

        # target in electrons
        target_es = self.electrons(target, exp_time) * fract

        # calculate different e- contributions
        n_target = target_es
        n_sky = self.electrons(sky_spec, exp_time)
        # read noise is independent per pixel, so it adds in quadrature over
        # the aperture (variance N*ron^2, not (N*ron)^2)
        n_ron = math.sqrt(self.eff_pixels) * self.camera.readout_noise * gain
        n_dark = self.eff_pixels * binning**2 * self.camera.dark_current * gain * exp_time

        # calculate S/N by using dimensionless values
        self.snr = n_target.value / math.sqrt(n_target.value + n_sky.value + n_dark.value + n_ron.value**2)

        # mag accuracy is 2.5 log ( 1 + N/S), see:
        # https://www.eso.org/~ohainaut/ccd/sn.html
        self.mag_accuracy = 2.5 * np.log10(1. + 1. / self.snr)

        # count rates
        self.target_counts = np.floor(n_target / gain)
        self.sky_counts = np.floor(n_sky / gain)
        self.ron_counts = np.floor(n_ron / gain)
        self.dark_counts = np.floor(n_dark / gain)

        # peak
        scale = scipy.special.erf(1/np.sqrt(8*sig2))**2
        self.peak = np.floor((target_es * scale + (n_sky + n_dark) / self.eff_pixels) / gain + bias)

    def solid_angle_of_aperture(self, aper_radius: u.arcsec):
        return math.pi * aper_radius ** 2

    def electrons(self, spectrum, exp_time) -> u.electron:
        """Calculate electrons.

        Args:
            spectrum: Spectrum, already multiplied with filter and QE.
            exp_time: Exposure time.
        """

        # number of electrons per nm
        # energy is E=h*c/lam, number is N=flux*exp_time*A/E
        n = spectrum.y * exp_time * self.telescope.effective_area() / (const.h * const.c / spectrum.x)

        # integrate over wavelength
        electrons = trapz(n, spectrum.x).to(u.dimensionless_unscaled)

        # unit is e-
        return electrons * u.electron

    def arcsec_per_pixel(self, binning: int = 1) -> float:
        return self.camera.pixel_size * binning * self.telescope.plate_scale

    def pixels_in_aperture(self, aper_radius: u.arcsec, seeing: Angle, binning: int = 1) -> int:
        return int(np.floor(self.solid_angle_of_aperture(aper_radius) / self.arcsec_per_pixel(binning)**2))
