"""Cohérence de la version : application, journal des modifications, README et notes de version."""
import glob
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


class ReleaseConsistencyTests(unittest.TestCase):
    def app_version(self):
        return re.search(r'^APP_VERSION = "([\d.]+)"', read("app_utils.py"), re.M).group(1)

    def changelog_versions(self):
        return re.findall(r"^## \[v?([\d.]+)\] — (\d{4}-\d{2}-\d{2})", read("CHANGELOG.md"), re.M)

    def test_changelog_top_section_matches_app_version(self):
        versions = self.changelog_versions()
        self.assertTrue(versions)
        self.assertEqual(versions[0][0], self.app_version(), "la 1re section du CHANGELOG doit être la version de l'application")

    def test_changelog_versions_decrease_and_dates_do_not_go_backwards(self):
        versions = self.changelog_versions()
        as_tuple = lambda v: tuple(int(x) for x in v.split("."))
        for (v1, d1), (v2, d2) in zip(versions, versions[1:]):
            self.assertGreater(as_tuple(v1), as_tuple(v2), f"{v1} doit être plus récente que {v2}")
            self.assertGreaterEqual(d1, d2, f"la date de {v1} ({d1}) précède celle de {v2} ({d2})")

    def test_readme_announces_the_current_version(self):
        self.assertIn(f"## Nouveautés de la version {self.app_version()}", read("README.md"))

    def test_release_notes_file_matches_the_version_if_present(self):
        name = f"RELEASE_NOTES_{self.app_version()}.md"          # les notes des versions précédentes sont ignorées
        if os.path.exists(os.path.join(ROOT, name)):
            self.assertTrue(read(name).startswith(f"## [{self.app_version()}]"))

    def test_new_modules_are_documented_in_the_readme(self):
        readme = read("README.md")
        for module in ("dxf_import.py", "box_generator.py", "vector_import.py", "box_dialog.py", "settings_window.py"):
            if os.path.exists(os.path.join(ROOT, module)):
                self.assertIn(f"`{module}`", readme, f"{module} absent de la structure du README")


if __name__ == "__main__":
    unittest.main()
