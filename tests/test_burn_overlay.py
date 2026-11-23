"""Gravure en temps réel sur l'aperçu 2D : les traits gravés passent en rouge (Preview2DTab.update_burn)."""
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
        self.win.job_display.plot(GCODE)
        self.tab = self.win.tab_vector_2d

    def red_points(self):
        xs, _ys = self.tab.burn_overlay.getData()
        return [] if xs is None else [round(float(v), 3) for v in xs if v == v]

    def test_segments_are_mapped_to_streamed_lines(self):
        self.assertEqual(list(self.tab.burn.line_idx), [4, 5, 6])
        self.assertEqual(len(self.tab.burn.segments), 3)

    def test_head_in_the_middle_of_the_second_stroke(self):
        self.tab.set_lines_acked(7)                     # GRBL a tout accepté
        self.tab.update_burn(15.0, 0.0)        # tête au milieu du trait 1
        self.assertEqual(self.tab.burn.done, 1)       # trait 0 gravé
        self.assertEqual(self.red_points(), [0.0, 10.0, 10.0, 15.0])   # + trait 1 jusqu'à la tête

    def test_nothing_is_red_before_grbl_accepts_the_lines(self):
        self.tab.set_lines_acked(4)                     # aucun trait gravé encore accepté
        self.tab.update_burn(15.0, 0.0)
        self.assertEqual(self.tab.burn.done, 0)
        self.assertEqual(self.red_points(), [])

    def test_never_goes_back_and_finishes_all_red(self):
        self.tab.set_lines_acked(7)
        self.tab.update_burn(25.0, 0.0)
        self.tab.update_burn(5.0, 0.0)          # rapport en retard : on ne recule pas
        self.assertEqual(self.tab.burn.done, 2)
        self.tab.finish_burn(True)
        self.assertEqual(self.tab.burn.done, 3)

    def test_interrupted_job_keeps_what_was_engraved(self):
        self.tab.set_lines_acked(7)
        self.tab.update_burn(12.0, 0.0)
        self.tab.finish_burn(False)
        self.assertEqual(self.tab.burn.done, 1)

    def test_new_job_on_the_same_gcode_starts_from_zero(self):
        self.tab.set_lines_acked(7)
        self.tab.update_burn(25.0, 0.0)
        self.win.engraver.stream_starting.emit(GCODE)  # envoi du même G-Code : simple remise à zéro
        self.assertEqual((self.tab.burn.done, self.red_points()), (0, []))


if __name__ == "__main__":
    unittest.main()
