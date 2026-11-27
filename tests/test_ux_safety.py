"""Sécurité et erreurs silencieuses dans l'interface : arrêt d'urgence toujours accessible pendant un travail,
G-Code périmé signalé et confirmé avant l'envoi, molette sans effet sur un champ qui n'a pas le focus."""
import os
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtCore import QPoint, QPointF, Qt
    from PyQt6.QtGui import QWheelEvent
    from PyQt6.QtWidgets import QApplication, QDoubleSpinBox, QScrollArea, QVBoxLayout, QWidget
    from job_fakes import FakeDialogs, make_job
    from laser_studio.controllers import job as job_module
    from laser_studio.models import machine_state as ms
    from laser_studio.ui.app.menu import AppActions
    from laser_studio.ui.app.menu.toolbar import AppToolBar
    from laser_studio.ui.wheel_guard import install_wheel_guard
    from test_engraver_controller import make_engraver
except ImportError:  # PyQt6 manquant
    AppActions = None


@unittest.skipIf(AppActions is None, "PyQt6 non importable ici")
class EmergencyStopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_toolbar_button_shows_while_the_machine_works(self):
        actions = AppActions()
        toolbar = AppToolBar(actions)
        self.addCleanup(toolbar.deleteLater)
        self.assertEqual(actions.emergency_stop.shortcut().toString(), "F9")
        self.assertFalse(actions.emergency_stop.isEnabled())             # déconnecté
        self.assertFalse(toolbar.stop_button_action.isVisible())
        actions.set_machine_state(can_realtime=True, running=True)         # gravure, homing, cadrage…
        self.assertTrue(actions.emergency_stop.isEnabled())
        self.assertTrue(toolbar.stop_button_action.isVisible())
        stops = []
        actions.emergency_stop_requested.connect(lambda: stops.append(True))
        toolbar.stop_button.click()
        self.assertEqual(stops, [True])
        actions.set_machine_state(can_realtime=True, running=False)
        self.assertFalse(toolbar.stop_button_action.isVisible())

    def test_emergency_stop_resets_only_a_connected_engraver(self):
        engraver, connection, _dialogs, _events = make_engraver(connected=False)
        engraver.emergency_stop()
        connection.soft_reset.assert_not_called()
        engraver, connection, _dialogs, _events = make_engraver(state=ms.STREAMING)
        engraver.emergency_stop()
        connection.soft_reset.assert_called_once()


@unittest.skipIf(AppActions is None, "PyQt6 non importable ici")
class StaleGcodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def generated_job(self, gcode="G1 X1 S100"):
        """JobController qui vient de générer `gcode` (thread de génération simulé)."""
        worker = mock.Mock()
        with mock.patch.object(job_module, "AdvancedGCodeWorker", return_value=worker):
            job, _dialogs = make_job(image=np.zeros((4, 4), np.uint8))
            self.assertTrue(job.generate())
        job.generated.emit(gcode, 1, 0.0, 0.0)
        for call in worker.finished.connect.call_args_list[1:]:             # le suivi, après generated
            call[0][0](gcode, 1, 0.0, 0.0)
        return job

    def test_a_setting_changed_after_generation_makes_it_stale(self):
        job = self.generated_job()
        changes = []
        job.gcode_stale_changed.connect(changes.append)
        self.assertFalse(job.is_stale("G1 X1 S100"))
        job.grbl.update(frame_power_pct=2.0)                               # cadrage seulement : sans effet
        self.assertEqual(changes, [])
        job.layers.update(job.layers.layers[0].id, power=12.0)
        self.assertEqual(changes, [True])
        self.assertTrue(job.is_stale("G1 X1 S100"))
        self.assertFalse(job.is_stale("G1 X9 S5"))                         # autre G-Code (importé, retouché)
        job.generated.emit("G1 X2", 1, 0.0, 0.0)                          # nouvelle génération : plus périmé
        self.assertEqual(changes, [True, False])

    def test_imported_gcode_is_never_stale(self):
        job = self.generated_job()
        job.imported.emit("G1 X5", "fichier.gcode")
        job.layers.update(job.layers.layers[0].id, power=12.0)
        self.assertFalse(job.is_stale("G1 X5"))

    def test_sending_a_stale_gcode_asks_first(self):
        engraver, connection, dialogs, _events = make_engraver(gcode="G1 X1 S100", dialogs=FakeDialogs(answer=False),
                                                               gcode_stale=lambda text: True)
        self.assertFalse(engraver.send_job())
        self.assertEqual(dialogs.kinds(), ["confirm_default_no"])
        connection.start_stream.assert_not_called()


@unittest.skipIf(AppActions is None, "PyQt6 non importable ici")
class WheelGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        install_wheel_guard(cls.app)

    def wheel(self, widget):
        event = QWheelEvent(QPointF(5, 5), QPointF(widget.mapToGlobal(QPoint(5, 5))), QPoint(0, 0), QPoint(0, -120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                            False)
        QApplication.sendEvent(widget, event)

    def test_wheel_scrolls_the_panel_instead_of_changing_an_unfocused_value(self):
        area = QScrollArea()
        self.addCleanup(area.deleteLater)
        content = QWidget()
        layout = QVBoxLayout(content)
        spin = QDoubleSpinBox()
        spin.setRange(0, 100)
        spin.setValue(50)
        layout.addWidget(spin)
        layout.addSpacing(2000)                                          # panneau plus haut que la fenêtre
        area.setWidget(content)
        area.resize(200, 200)
        area.show()
        area.setFocus()                                                  # le champ n'a pas été choisi
        self.app.processEvents()
        self.assertFalse(spin.hasFocus())
        self.wheel(spin)
        self.assertEqual(spin.value(), 50)                               # valeur intacte
        self.assertGreater(area.verticalScrollBar().value(), 0)          # le panneau a défilé
        spin.setFocus()
        self.app.processEvents()
        if spin.hasFocus():                                              # focus réel (plateforme sans écran)
            self.wheel(spin)
            self.assertNotEqual(spin.value(), 50)                        # champ choisi : la molette le règle


if __name__ == "__main__":
    unittest.main()
