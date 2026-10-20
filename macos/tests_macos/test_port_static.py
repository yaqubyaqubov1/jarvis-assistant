"""Safe source-level tests runnable on macOS CI without GUI permissions."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MacPortTests(unittest.TestCase):
    def test_python_source_parses(self):
        for folder in ('ai', 'core', 'memory', 'tools', 'ui', 'voice', 'platforms'):
            for path in (ROOT / folder).glob('*.py'):
                with self.subTest(path=path):
                    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))

    def test_tools_registered(self):
        text = (ROOT / 'tools' / 'apps.py').read_text(encoding='utf-8')
        for name in ('open_application', 'close_application', 'close_all_apps',
                     'list_applications', 'list_windows', 'get_active_window'):
            with self.subTest(name=name):
                self.assertIn(f"@register('{name}'", text)

    def test_mac_requirements_are_windows_free(self):
        contents = (ROOT / 'requirements-macos.txt').read_text().lower()
        for package in ('pywin32', 'pygetwindow', 'screen-brightness-control'):
            self.assertNotIn(package, contents)

    def test_mac_launcher_exists(self):
        self.assertTrue((ROOT / 'setup_macos.command').exists())
        self.assertTrue((ROOT / 'Jarvis.command').exists())


if __name__ == '__main__':
    unittest.main()
