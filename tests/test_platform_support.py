import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from platform_support import default_data_dir

class PlatformTests(unittest.TestCase):
    def test_mac_uses_application_support_not_windows_environment(self):
        home = Path('/Users/example')
        self.assertEqual(default_data_dir('darwin', home, {'LOCALAPPDATA': 'wrong'}),
                         home / 'Library' / 'Application Support' / 'SchwiDesktopPet')

    def test_windows_keeps_existing_settings_path(self):
        self.assertEqual(default_data_dir('win32', '/home/example', {'LOCALAPPDATA': '/local'}),
                         Path('/local/SchwiDesktopPet'))

if __name__ == '__main__':
    unittest.main()
