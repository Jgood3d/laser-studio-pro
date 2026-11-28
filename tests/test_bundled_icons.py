"""Chaque icône Breeze nommée dans le code est dans le pack embarqué (resources/icons/breeze/22x22) : sinon le bouton
s'affiche sans icône (bug : « Fond caméra » de l'éditeur vectoriel, camera-photo absente du pack)."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent / "src" / "laser_studio"
PATTERNS = (
    r'(?:palette_icon|bundled_icon|tool_button|_action)\(\s*"([a-z0-9-]+)"',
    r'icon_name="([a-z0-9-]+)"',
    r'\(\s*"[a-z_]+",\s*"[a-z_.]+",\s*"([a-z0-9-]+)"\s*\)',      # tables (commande, clé, icône)
)


class BundledIconsTests(unittest.TestCase):
    def test_every_named_icon_is_bundled(self):
        bundled = {p.stem for p in (ROOT / "resources" / "icons" / "breeze" / "22x22").rglob("*.svg")}
        used = set()
        for path in ROOT.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for pattern in PATTERNS:
                used.update(name for name in re.findall(pattern, text) if "-" in name)
        self.assertIn("camera-photo", used)
        self.assertEqual(sorted(used - bundled), [])


if __name__ == "__main__":
    unittest.main()
