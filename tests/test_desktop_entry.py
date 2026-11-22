"""Fichier .desktop de Linux (packaging/linux/) : nom, icône et commande
cohérents avec l'identifiant de l'application et la commande installée."""
import configparser
import os
import re
import shutil
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))

from laser_studio.core.version import APP_ID  # noqa: E402

DESKTOP = os.path.join(REPO, "packaging", "linux", f"{APP_ID}.desktop")


def read_desktop():
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str                     # clés sensibles à la casse (Name[fr]…)
    parser.read(DESKTOP, encoding="utf-8")
    return parser


def gui_script():
    """Nom de la commande déclarée dans [project.gui-scripts] de pyproject.toml."""
    text = open(os.path.join(REPO, "pyproject.toml"), encoding="utf-8").read()
    section = text.split("[project.gui-scripts]", 1)[1]
    return re.search(r'^([\w-]+)\s*=\s*"laser_studio\.main:main"', section, re.M).group(1)


class DesktopEntryTests(unittest.TestCase):
    def test_file_is_named_after_the_app_id(self):
        self.assertTrue(os.path.isfile(DESKTOP), DESKTOP)

    def test_icon_is_the_app_id(self):
        self.assertEqual(read_desktop()["Desktop Entry"]["Icon"], APP_ID)

    def test_exec_runs_the_installed_command(self):
        desktop = read_desktop()
        command = gui_script()
        self.assertEqual(desktop["Desktop Entry"]["Exec"], command)
        self.assertEqual(desktop["Desktop Action stencil-studio"]["Exec"], f"{command} --stencil-studio")

    def test_translated_in_the_four_languages(self):
        entry = read_desktop()["Desktop Entry"]
        for key in ("GenericName", "Comment", "Keywords"):
            for lang in ("fr", "de", "es"):
                self.assertIn(f"{key}[{lang}]", entry)

    @unittest.skipIf(shutil.which("desktop-file-validate") is None, "desktop-file-validate absent")
    def test_desktop_file_validate(self):
        result = subprocess.run(["desktop-file-validate", DESKTOP], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
