import math
import os
from typing import Dict, TypeVar, Tuple, List, Union
import astropy.units as u
import numpy as np
import scipy
from astropy import constants as const
from astropy.coordinates import Angle
from astropy.units import Unit, UnitBase, Quantity

from goetc.spectrum import XYData, Bandpass, Spectrum


def data_path():
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


def mag2flux(mag: u.mag, flux0=1.):
    return flux0 * 10.**(-0.4 * mag.value)


def flux2mag(flux: float, flux0=1.):
    return -2.5*np.log10(flux/flux0)*u.mag


def c(value, unit, float_unit=None):
    # if no float type is given, it's the same as unit
    if float_unit is None:
        float_unit = unit

    # if float is given, assign unit
    if not isinstance(value, Quantity):
        value = value * float_unit

    # return final unit
    return value.to(unit)


T = TypeVar('T')


def create_objects(config: dict, group: str, cls: T) -> Dict[str, T]:
    # doesn't exist?
    if group not in config:
        print('Collection of %s not found in config.' % group)
        return {}

    # create objects
    coll: Dict[str, T] = {}
    for name, cfg in config[group].items():
        # create object
        coll[name] = cls(**cfg)

    # finished
    return coll


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
        self.qe = qe
        self.optics = optics

        # QE given as string?
        self.qe_name = None
        if isinstance(qe, str):
            from .config import CONFIG
            self.qe_name = qe
            self.qe = CONFIG.sensor(qe)

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
            magnitude: Magnitude of sky in same filter as simulation.
            seeing: Seeing in arcsec.
            flux: Flux in W/m^2/m/steradian
            airmass: Airmass
            extinction: Extinction
        """

        # store
        self.magnitude = magnitude
        self.seeing = Angle(c(seeing, u.arcsec))
        self.airmass = airmass
        self.extinction = c(extinction, u.mag)

    def flux(self, bandpass: Bandpass):
        from .config import CONFIG

        # calculate area of 1 arcsec square
        sqrarcs = (1. * u.arcsec).to(u.radian) ** 2

        # get vega spectrum and integrate over bandpass
        vega = CONFIG.vega_spectrum()
        flux = bandpass.integrate(vega)
        print(flux)

        # scale by



class Simulation:
    def __init__(self, telescope: Telescope, camera: Camera, bandpass: Bandpass):
        """

        Args:
            exposure_time: Exposure time in secs
            snr: Signal-to-noise ratio
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
        self.plate_scale = 0.
        self.mag_accuracy = 0.
        self.peak = 0

        # observation defined from 2 of the following 3 quantities
        self.snr = 0.
        self.exp_time = 0.
        self.magnitude = 0.

    def get_signal_to_noise(self, exp_time: float, target: Spectrum, sky: Sky, aper_radius: Angle, binning: int):
        from goetc.config import CONFIG

        # target brightness in filter (before QE, extinction)
        magn = self.filter.mag(target)*u.mag

        # gain and bias
        gain = self.camera.gain_binning(binning)
        bias = self.camera.bias_binning(binning)

        # apply QE and filter to target spectrum
        target = self.filter.apply(self.camera.qe.apply(target))

        # same for sky, but we just get the flux of vega, scaled to sky brightness and to 1 arcsec^2
        vega = CONFIG.vega_spectrum().norm_to_mag(self.filter, sky.magnitude)
        sky_spec = self.filter.apply(self.camera.qe.apply(vega))
        sky_spec.data.y *= self.solid_angle_of_aperture(aper_radius) / (1. * u.arcsec).to(u.radian)**2

        # extinction
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
        n_ron = self.eff_pixels * self.camera.readout_noise * gain
        n_dark = self.eff_pixels * binning**2 * self.camera.dark_current * gain * exp_time

        # calculate S/N by using dimensionless values
        self.snr = n_target.value / math.sqrt(n_target.value + n_sky.value + n_dark.value + n_ron.value**2)
        self.exp_time = exp_time
        self.magnitude = magn

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

    def get_exposure_time(self, snr: float, target: Spectrum, sky: Sky, aper_radius: Angle, binning: int):
        """
        Same as get_signal_to_noise() but calculates exposure time from a given S/N using
        an exposure time factor "ft" given the target, dark, and sky values for 1sec:

            snr = target*ft / sqrt (target*ft + dark*ft + sky*ft + ron**2)
            target*ft + dark*ft + sky*ft + ron**2 = target**2 * ft**2 / snr**2
            ft**2 (target**2 / snr**2) + ft (-target-dark-sky) + (-ron**2) = 0
        """
        from goetc.config import CONFIG

        # target brightness in filter (before QE, extinction)
        magn = self.filter.mag(target)*u.mag

        # gain and bias
        gain = self.camera.gain_binning(binning)
        bias = self.camera.bias_binning(binning)

        # apply QE and filter to target spectrum
        target = self.filter.apply(self.camera.qe.apply(target))

        # same for sky, but we just get the flux of vega, scaled to sky brightness and to 1 arcsec^2
        vega = CONFIG.vega_spectrum().norm_to_mag(self.filter, sky.magnitude)
        sky_spec = self.filter.apply(self.camera.qe.apply(vega))
        sky_spec.data.y *= self.solid_angle_of_aperture(aper_radius) / (1. * u.arcsec).to(u.radian)**2

        # extinction
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

        # unit exposure time
        t0 = 1.*u.s

        # target in electrons for 1sec exposure
        target_es = self.electrons(target, t0) * fract

        # calculate different e- contributions for 1sec exposures
        n_target = target_es
        n_sky = self.electrons(sky_spec, t0)
        n_ron = self.eff_pixels * self.camera.readout_noise * gain
        n_dark = self.eff_pixels * binning**2 * self.camera.dark_current * gain * t0

        # calculate exposure time from S/N using dimensionless values
        a = n_target.value**2/snr**2
        b = -n_target.value-n_sky.value-n_dark.value
        c = -n_ron.value**2
        discr = b**2-4*a*c
        if discr < 0. : raise ValueError ('get_exptime() : no real roots')
        root1 = 0.5*(-b+np.sqrt(discr))/a
        root2 = 0.5*(-b-np.sqrt(discr))/a
        ft = max(root1,root2)
        if ft <= 0. : raise ValueError ('get_target_brightness() < 0')

        # save results
        self.exp_time = t0*ft
        self.snr = snr
        self.magnitude = magn

        # mag accuracy is 2.5 log ( 1 + N/S), see:
        # https://www.eso.org/~ohainaut/ccd/sn.html
        self.mag_accuracy = 2.5 * np.log10(1. + 1. / self.snr)

        # count rates
        self.target_counts = np.floor(n_target*ft / gain)
        self.sky_counts = np.floor(n_sky*ft / gain)
        self.ron_counts = np.floor(n_ron*ft / gain)
        self.dark_counts = np.floor(n_dark*ft / gain)

        # peak
        scale = scipy.special.erf(1/np.sqrt(8*sig2))**2
        self.peak = np.floor(ft*(target_es * scale + (n_sky + n_dark) / self.eff_pixels) / gain + bias)

    def get_magnitude (self, snr: float, exp_time: float, target: Spectrum, sky: Sky, aper_radius: Angle, binning: int):
        """
        Same as get_signal_to_noise() but calculates target brightness from a given S/N and
        exposure time using a target brightness factor ft :

            snr = target*ft / sqrt (target*ft + dark + sky + ron**2)
            target*ft + dark + sky + ron**2 = target**2 * ft**2 / snr**2
            ft**2 (target**2 / snr**2) + ft (-target) + (-dark-sky-ron**2) = 0
        """
        from goetc.config import CONFIG

        # target brightness in filter (before QE, extinction)
        magn = self.filter.mag(target)*u.mag

        # gain and bias
        gain = self.camera.gain_binning(binning)
        bias = self.camera.bias_binning(binning)

        # apply QE and filter to target spectrum
        target = self.filter.apply(self.camera.qe.apply(target))

        # same for sky, but we just get the flux of vega, scaled to sky brightness and to 1 arcsec^2
        vega = CONFIG.vega_spectrum().norm_to_mag(self.filter, sky.magnitude)
        sky_spec = self.filter.apply(self.camera.qe.apply(vega))
        sky_spec.data.y *= self.solid_angle_of_aperture(aper_radius) / (1. * u.arcsec).to(u.radian)**2

        # extinction
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
        n_ron = self.eff_pixels * self.camera.readout_noise * gain
        n_dark = self.eff_pixels * binning**2 * self.camera.dark_current * gain * exp_time

        # calculate flux by using dimensionless values
        # ft**2 (target**2 / snr**2) + ft (-target) + (-dark-sky-ron**2) = 0
        a = n_target.value**2/snr**2
        b = -n_target.value
        c = -n_sky.value-n_dark.value-n_ron.value**2
        discr = b**2-4*a*c
        if discr < 0. : raise ValueError ('get_target_brightness() : no real roots')
        root1 = 0.5*(-b+np.sqrt(discr))/a
        root2 = 0.5*(-b-np.sqrt(discr))/a
        ft = max(root1,root2)
        if ft <= 0. : raise ValueError ('get_target_brightness() < 0')

        # save results
        self.exp_time = exp_time
        self.snr = snr
        self.magnitude = magn+flux2mag(ft)

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
        electrons = np.trapz(n, spectrum.x).to(u.dimensionless_unscaled)

        # unit is e-
        return electrons * u.electron

    def arcsec_per_pixel(self, binning: int = 1) -> float:
        return self.camera.pixel_size * binning * self.telescope.plate_scale

    def pixels_in_aperture(self, aper_radius: u.arcsec, seeing: Angle, binning: int = 1) -> int:
        return int(np.floor(self.solid_angle_of_aperture(aper_radius) / self.arcsec_per_pixel(binning)**2))
