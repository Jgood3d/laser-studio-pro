"""Autotest de Stencil Studio (src/stencil_studio/selftest.py) : mêmes résultats que les valeurs
attendues (OpenCV, numpy, scipy, moteur du Studio), et page web à la même version que core.py.
Lancé ici pour qu'il ne se casse plus sans que personne le voie."""
import os
import subprocess
import sys
import unittest

STUDIO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "stencil_studio")

try:
    import cv2  # noqa: F401
    import scipy  # noqa: F401
except ImportError:  # OpenCV, SciPy manquants
    cv2 = None


@unittest.skipIf(cv2 is None, "OpenCV / SciPy non importables ici")
class StencilSelftestTests(unittest.TestCase):
    def test_selftest_is_conform(self):
        # Lancé comme un utilisateur le ferait (« py selftest.py » dans le dossier du Studio).
        run = subprocess.run([sys.executable, "selftest.py"], cwd=STUDIO, capture_output=True, text=True, timeout=300)
        self.assertEqual(run.returncode, 0, run.stdout[-3000:] + run.stderr[-3000:])
        self.assertIn("Tout est conforme.", run.stdout)


if __name__ == "__main__":
    unittest.main()
