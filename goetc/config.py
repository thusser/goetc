import glob
import itertools
import os
import shutil
from enum import Enum
from typing import List, Type
import re
import pandas as pd
import yaml

import goetc
from goetc.simulation import Camera, Telescope
from goetc.spectrum import XYData, QE, Spectrum, Bandpass


class DATA(Enum):
    TELESCOPE = 'telescope'
    CAMERA = 'camera'
    TRANSMISSION = 'transmission'
    BANDPASS = 'bandpass'
    SPECTRUM = 'spectrum'


class TRANSMISSION(Enum):
    SENSOR = 'sensor'
    

def snake(text: str):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower().replace(' ', '')


def desnake(text: str):
    return ' '.join(word.title() for word in text.split('_'))


class Config:
    def __init__(self):
        self._path: str = ''
        self._config = {}

    def init(self, copy: bool = False):
        # path to data
        data_path = os.path.join(os.path.abspath(os.path.dirname(goetc.__file__)), 'data')

        # get path for configuration
        if 'APPDATA' in os.environ:
            config_home = os.environ['APPDATA']
        elif 'XDG_CONFIG_HOME' in os.environ:
            config_home = os.environ['XDG_CONFIG_HOME']
        else:
            config_home = os.path.join(os.environ['HOME'], '.config')
        self._path = os.path.join(config_home, 'astroetc')

        # directory does not exist?
        if copy and not os.path.exists(self._path):
            # create it and copy all files
            shutil.copytree(goetc.data_path(), self._path, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__*'))

        # now, does path exist?
        if not os.path.exists(self._path):
            self._path = data_path

        # find all cameras, bandpasses, etc
        self._config[DATA.CAMERA] = self._list_yaml(DATA.CAMERA)
        self._config[DATA.BANDPASS] = self._list_csv(DATA.BANDPASS, recursive=True)
        self._config[DATA.TRANSMISSION] = self._list_csv(DATA.TRANSMISSION, recursive=True)
        self._config[DATA.TELESCOPE] = self._list_yaml(DATA.TELESCOPE)
        self._config[DATA.SPECTRUM] = self._list_csv(DATA.SPECTRUM)

    def _list_yaml(self, category: DATA, group: str = None):
        filenames = [os.path.basename(f) for f in glob.glob(self._data_path('*.yaml', category=category))]
        return {self._get_yaml_name(f, category, group): f for f in filenames}

    def _load_yaml(self, filename: str, category: DATA = None, group: str = None):
        with open(self._data_path(filename, category, group), 'r') as f:
            return yaml.safe_load(f)

    def _get_yaml_name(self, filename: str, category: str = None, group: str = None):
        return self._load_yaml(filename, category, group)['name']

    def _list_csv(self, category: DATA, group: str = None, recursive: bool = False):
        if recursive:
            groups = next(os.walk(self._data_path(category=category)))[1]
            return {group: self._list_csv(category, group) for group in groups}
        else:
            data = pd.read_csv(self._data_path('index.csv', category, group), index_col=False)
            return {row['name']: row['filename'] for _, row in data.iterrows()}

    def _data_path(self, filename: str = None, category: DATA = None, group: str = None):
        parts = [self._path] + [p for p in [category.value, group, filename] if p is not None]
        return os.path.join(*parts)

    def path(self, filename: str = None, category: DATA = None, group: str = None):
        # define parts of path
        parts = [self._path]

        # got a category?
        if category is not None:
            if category not in self._config:
                raise ValueError('Category not found.')
            parts += [category.value]

            # got a group?
            if group is not None:
                if group not in self._config[category]:
                    raise ValueError('Group group not found.')
                parts += [group]

        # build it
        parts += [filename]
        return os.path.join(*parts)

    def groups(self, category: str):
        if isinstance(self._config[category], dict):
            return list(self._config[category].keys())
        else:
            raise ValueError

    def recursive_groups(self, category: str):
        groups = sorted(CONFIG.groups(category))
        return list(itertools.chain(*[[f'{g}/{f}' for f in CONFIG.group_entries(category, g)] for g in groups]))

    def group_entries(self, category: str, group: str = None):
        # get data
        data = self._config[category] if group is None else self._config[category][group]

        # what type?
        if isinstance(data, dict):
            return list(data.keys())
        elif isinstance(data, list):
            return data
        else:
            raise ValueError

    def group_path(self, category: str, group: str = None, filename: str = None):
        path = os.path.join(self._path, category)
        if group is not None:
            path = os.path.join(path, group)
        return path if filename is None else os.path.join(path, filename)

    def camera(self, name: str):
        if name not in self._config[DATA.CAMERA]:
            raise ValueError('Camera "%s" not found.' % name)
        filename = self._config[DATA.CAMERA][name]
        return Camera(**self._load_yaml(filename, category=DATA.CAMERA))

    def sensor(self, name: str):
        if name not in self._config[DATA.TRANSMISSION][TRANSMISSION.SENSOR.value]:
            raise ValueError('Sensor "%s" not found.' % name)
        filename = self._config[DATA.TRANSMISSION][TRANSMISSION.SENSOR.value][name]
        return QE(self.path(filename, DATA.TRANSMISSION, TRANSMISSION.SENSOR.value))

    def telescope(self, name: str):
        if name not in self._config[DATA.TELESCOPE]:
            raise ValueError('Telescope "%s" not found.' % name)
        filename = self._config[DATA.TELESCOPE][name]
        return Telescope(**self._load_yaml(filename, category=DATA.TELESCOPE))

    def bandpass(self, name: str):
        group, bandpass = name.split('/')
        return Bandpass(self.path(self._config[DATA.BANDPASS][group][bandpass], category=DATA.BANDPASS, group=group))

    def spectrum(self, name: str):
        return Spectrum(self.path(self._config[DATA.SPECTRUM][name], category=DATA.SPECTRUM))


CONFIG = Config()


__all__ = ['CONFIG', 'DATA']
