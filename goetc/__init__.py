import os


def data_path():
    """Absolute path to the package data directory."""
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
