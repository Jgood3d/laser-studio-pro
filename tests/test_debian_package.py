"""Paquet Debian (packaging/debian) : chaque dépendance de pyproject.toml a son paquet Debian dans
debian/control, les fichiers de l'application sont installés, le script de construction est exécutable."""
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBIAN = os.path.join(REPO, "packaging", "debian")

# Dépendance PyPI -> paquet Debian.
DEBIAN_NAMES = {
    "numpy": "python3-numpy", "opencv-python-headless": "python3-opencv", "pillow": "python3-pil",
    "PyQt6": "python3-pyqt6", "PyQt6-WebEngine": "python3-pyqt6.qtwebengine", "pyqtgraph": "python3-pyqtgraph",
    "pyserial": "python3-serial", "pyyaml": "python3-yaml", "scikit-image": "python3-skimage",
    "scipy": "python3-scipy", "svg.path": "python3-svg.path",
}


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


class DebianPackageTests(unittest.TestCase):
    def test_every_python_dependency_has_its_debian_package(self):
        pyproject = read(REPO, "pyproject.toml")
        block = pyproject[pyproject.index("dependencies = ["):]
        deps = re.findall(r'^\s+"([^"]+)",', block[:block.index("]")], re.M)
        control = read(DEBIAN, "debian", "control")
        depends = control[control.index("Depends:", control.index("Package:")):control.index("Recommends:")]
        for dep in deps:
            self.assertIn(dep, DEBIAN_NAMES, f"{dep} : paquet Debian à ajouter à DEBIAN_NAMES et debian/control")
            self.assertRegex(depends, rf"\b{re.escape(DEBIAN_NAMES[dep])}\b", dep)

    def test_qt_is_recent_enough(self):
        # QIcon.ThemeIcon (Qt 6.7) : sans cette borne, le paquet s'installait sur Ubuntu 24.04 et plantait.
        self.assertIn("python3-pyqt6 (>= 6.7)", read(DEBIAN, "debian", "control"))

    def test_desktop_entry_icon_and_metainfo_are_installed(self):
        rules = read(DEBIAN, "debian", "rules")
        for target in ("usr/share/applications/", "usr/share/icons/hicolor/512x512/apps/", "usr/share/metainfo/"):
            self.assertIn(target, rules)
        for name in ("io.github.jgood3d.LaserStudioPro.desktop", "io.github.jgood3d.LaserStudioPro.metainfo.xml"):
            self.assertTrue(os.path.exists(os.path.join(REPO, "packaging", "linux", name)), name)

    def test_scripts_are_executable(self):
        for path in (os.path.join(DEBIAN, "build-deb.sh"), os.path.join(DEBIAN, "debian", "rules")):
            self.assertTrue(os.access(path, os.X_OK), path)


if __name__ == "__main__":
    unittest.main()
