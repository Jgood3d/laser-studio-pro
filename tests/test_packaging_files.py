"""Fichiers de compilation versionnés : un .spec utilisé par les scripts de
build ne doit pas être ignoré par Git (le .gitignore ignore les *.spec
générés par PyInstaller). Sinon la compilation marche sur le poste de celui
qui l'a écrit, mais échoue dans la CI et chez les autres."""
import os
import re
import shutil
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_SCRIPTS = (
    "packaging/linux/build-linux.sh",
    "packaging/windows/build.bat",
    "packaging/macos/build_macos.sh",
    ".github/workflows/release.yml",
    ".github/workflows/macos-build.yml",
)


def specs_used_by_build_scripts():
    specs = set()
    for name in BUILD_SCRIPTS:
        path = os.path.join(REPO, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.lstrip().startswith(("#", "rem")):
                    continue
                for spec in re.findall(r"packaging[\\/][\w/\\]+\.spec", line):
                    specs.add(spec.replace("\\", "/"))
    return specs


@unittest.skipUnless(shutil.which("git") and os.path.isdir(os.path.join(REPO, ".git")),
                     "dépôt Git non disponible")
class PackagingFilesTests(unittest.TestCase):
    def test_build_specs_are_not_ignored_by_git(self):
        specs = specs_used_by_build_scripts()
        self.assertIn("packaging/pyinstaller/LaserStudioPro.spec", specs)
        for spec in specs:
            ignored = subprocess.run(["git", "check-ignore", "-q", "--no-index", spec],
                                     cwd=REPO).returncode == 0
            self.assertFalse(ignored, f"{spec} est ignoré par .gitignore")
            self.assertTrue(os.path.exists(os.path.join(REPO, spec)), f"{spec} absent")


if __name__ == "__main__":
    unittest.main()
