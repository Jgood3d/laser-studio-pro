"""Gravure en temps réel sur l'aperçu 2D : les traits gravés passent en rouge (update_burn_overlay)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# Préférences et données de l'application isolées : le test ne touche pas à celles de l'utilisateur.
_TMP = tempfile.mkdtemp()
os.environ.setdefault("XDG_CONFIG_HOME", _TMP)
os.environ.setdefault("XDG_DATA_HOME", _TMP)

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio import main_window
except ImportError:  # PyQt6, pyqtgraph... manquants
    main_window = None

# Trois traits gravés sur une ligne Y=0 (lignes n° 4, 5, 6 de l'envoi), après un déplacement à vide.
GCODE = "\n".join([
    "; --- PHASE 1 : GRAVURE IMAGE ---",
    "G21", "G90", "M4 S0",              # lignes 0, 1, 2
    "G0 X0 Y0",                         # ligne 3 : déplacement, pas gravé
    "G1 X10 S500 F1000",                # ligne 4 : trait 0
    "G1 X20 S800",                      # ligne 5 : trait 1
    "G1 X30 S200",                      # ligne 6 : trait 2
    "M5",
])


@unittest.skipIf(main_window is None, "main_window non importable ici")
class BurnOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # Préchauffage de Stencil Studio (QTimer 3 s) : QtWebEngine plante hors écran.
        mock.patch("laser_studio.ui.app.window_controller.preload_stencil_studio").start()
        cls.win = main_window.FullLaserStudio()

    def setUp(self):
        self.win.plot_gcode_preview(GCODE)

    def red_points(self):
        xs, _ys = self.win.burn_overlay.getData()
        return [] if xs is None else [round(float(v), 3) for v in xs if v == v]

    def test_segments_are_mapped_to_streamed_lines(self):
        self.assertEqual(list(self.win._burn_line_idx), [4, 5, 6])
        self.assertEqual(len(self.win._burn_segs), 3)

    def test_head_in_the_middle_of_the_second_stroke(self):
        self.win.on_lines_acked(7)                     # GRBL a tout accepté
        self.win.update_burn_overlay(15.0, 0.0)        # tête au milieu du trait 1
        self.assertEqual(self.win._burn_done, 1)       # trait 0 gravé
        self.assertEqual(self.red_points(), [0.0, 10.0, 10.0, 15.0])   # + trait 1 jusqu'à la tête

    def test_nothing_is_red_before_grbl_accepts_the_lines(self):
        self.win.on_lines_acked(4)                     # aucun trait gravé encore accepté
        self.win.update_burn_overlay(15.0, 0.0)
        self.assertEqual(self.win._burn_done, 0)
        self.assertEqual(self.red_points(), [])

    def test_never_goes_back_and_finishes_all_red(self):
        self.win.on_lines_acked(7)
        self.win.update_burn_overlay(25.0, 0.0)
        self.win.update_burn_overlay(5.0, 0.0)          # rapport en retard : on ne recule pas
        self.assertEqual(self.win._burn_done, 2)
        self.win.finish_burn_overlay(True)
        self.assertEqual(self.win._burn_done, 3)

    def test_interrupted_job_keeps_what_was_engraved(self):
        self.win.on_lines_acked(7)
        self.win.update_burn_overlay(12.0, 0.0)
        self.win.finish_burn_overlay(False)
        self.assertEqual(self.win._burn_done, 1)

    def test_new_job_on_the_same_gcode_starts_from_zero(self):
        self.win.on_lines_acked(7)
        self.win.update_burn_overlay(25.0, 0.0)
        self.win._prepare_burn_overlay(GCODE)          # même G-Code : simple remise à zéro
        self.assertEqual((self.win._burn_done, self.red_points()), (0, []))


if __name__ == "__main__":
    unittest.main()
