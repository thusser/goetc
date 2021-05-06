from __future__ import annotations
import os
import numpy as np
import pandas as pd
from numpy import trapz
import astropy.units as u
from scipy.interpolate import interp1d


class XYData:
    def __init__(self, filename: str = None,
                 x: np.ndarray = None, x_unit=u.nm,
                 y: np.ndarray = None, y_unit=u.erg/u.second/u.cm**2/u.nm):
        self.x = x
        self.y = y

        if filename is not None:
            data = pd.read_csv(filename, index_col=False, names=['x', 'y'], comment='#')
            self.x = data['x'].values * x_unit
            self.y = data['y'].values * y_unit

    def resample(self, ref_data: XYData) -> XYData:
        # interpolate linearly
        ip = interp1d(x=self.x, y=self.y, kind='linear', bounds_error=False, fill_value=0.)

        # create and return new Data
        return XYData(x=ref_data.x.copy(), y=ip(ref_data.x))

    def norm_area(self) -> XYData:
        area = trapz(self.y, self.x)
        return XYData(x=self.x, y=self.y / area)


class Spectrum:
    def __init__(self, filename: str = None, x: np.ndarray = None, y: np.ndarray = None):
        # load data
        self.data = XYData(filename=filename, x=x, y=y)

    @property
    def x(self):
        return self.data.x

    @property
    def y(self):
        return self.data.y

    def norm_to_mag(self, bandpass: Bandpass, mag: float) -> Spectrum:
        # calculate mag
        cur_mag = bandpass.mag(self)

        # normalize to given magnitude
        return Spectrum(x=self.x, y=self.y * np.power(100., 0.2 * (cur_mag - mag)))


class QE:
    def __init__(self, filename: str = None, x: np.ndarray = None, y: np.ndarray = None):
        # load data
        self.data = XYData(filename=filename, x=x, y=y, y_unit=u.dimensionless_unscaled)

        # y from percent to 0..1
        self.data.y /= 100.

    def apply(self, spec: Spectrum) -> Spectrum:
        qe = self.data.resample(spec.data)
        return Spectrum(x=spec.x, y=spec.y * qe.y)

    @property
    def x(self):
        return self.data.x

    @property
    def y(self):
        return self.data.y


class Bandpass:
    def __init__(self, filename: str = None):
        # load filter
        self.data = XYData(filename, y_unit=u.dimensionless_unscaled)
        self.resampled_data = None

        # load vega
        from .config import CONFIG
        self._vega = CONFIG.vega_spectrum()
        #self._vega = XYData(CONFIG.path('vega.csv'))
        self._vega_filter = self.data.resample(self._vega).norm_area()

    @property
    def x(self):
        return self.data.x

    @property
    def y(self):
        return self.data.y

    def apply(self, spec: Spectrum) -> Spectrum:
        bp = self.data.resample(spec.data)
        return Spectrum(x=spec.x, y=spec.y * bp.y)

    def mag(self, spec: Spectrum) -> float:
        # resample filter
        fltr = self.data.resample(spec.data)

        # multiply spectra with filter
        filter_spec = spec.y * fltr.y
        filter_vega = self._vega.y * self._vega_filter.y

        # integrate
        flux1 = trapz(filter_spec, spec.x) / trapz(fltr.y, fltr.x)
        flux2 = trapz(filter_vega, self._vega.x) / trapz(self._vega_filter.y, self._vega_filter.x)

        # calculate Vega magnitude
        return -2.5 * np.log10(flux1 / flux2)

    def integrate(self, spec: Spectrum) -> float:
        # resample filter
        fltr = self.data.resample(spec.data)

        # apply filter and integrate
        fs = spec.y * fltr.y
        return trapz(fs, spec.x)
