"""Platform-specific paths, kept independent of the GUI for direct tests."""
import os
from pathlib import Path
import sys

APP_VERSION = '1.1.0'


def default_data_dir(platform=None, home=None, environ=None):
    platform = sys.platform if platform is None else platform
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    if platform == 'darwin':
        return home / 'Library' / 'Application Support' / 'SchwiDesktopPet'
    if platform == 'win32':
        return Path(environ.get('LOCALAPPDATA', str(home))) / 'SchwiDesktopPet'
    return Path(environ.get('XDG_DATA_HOME', str(home / '.local' / 'share'))) / 'SchwiDesktopPet'
