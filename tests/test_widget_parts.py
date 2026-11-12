"""Morceaux d'interface sortis des pages et panneaux : GrblSettingsBox,
ImageTestGroup, SentGcodeLog, RealtimeCommands."""

import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "src", "laser_studio")
sys.path.insert(0, os.path.dirname(ROOT))

try:
    from PIL import Image
    from PyQt6.QtWidgets import QApplication, QPushButton, QToolButton
    from laser_studio.i18n import tr
    from laser_studio.ui.machine.controls.realtime_commands import RealtimeCommands
    from laser_studio.ui.machine.job_position import JobPositionBox
    from laser_studio.ui.settings.machine_params import MachineParamsPage
    from laser_studio.ui.settings.grbl_config.settings_box import GrblSettingsBox
    from laser_studio.ui.settings.test_matrix.image_test_group import ImageTestGroup
    from laser_studio.ui.machine.sent_gcode import SentGcodeLog
except ImportError:  # PyQt6 manquant
    GrblSettingsBox = None


def record(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


@unittest.skipIf(GrblSettingsBox is None, "PyQt6 non importable ici")
class WidgetPartsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, cls):
        widget = cls()
        self.addCleanup(widget.deleteLater)
        return widget

    def test_grbl_settings_buttons(self):
        box = self.make(GrblSettingsBox)
        for key, signal in (
            ("ui.grbl_read", box.read_requested),
            ("ui.grbl_send", box.send_requested),
            ("ui.grbl_export", box.export_requested),
            ("ui.grbl_import", box.import_requested),
            ("ui.grbl_link_profile", box.link_to_profile_requested),
        ):
            received = record(signal)
            next(
                b for b in box.findChildren(QPushButton) if b.text() == tr(key)
            ).click()
            self.assertEqual(received, [()], key)

    def test_image_test_group_shows_the_tile(self):
        group = self.make(ImageTestGroup)
        self.assertFalse(group.isChecked())
        group.set_source_image(Image.new("L", (300, 200)), "photo.png", 120.0)
        self.assertEqual(group.image_name_label.text(), "photo.png")
        self.assertEqual(group.image_width_spin.value(), 120.0)
        self.assertTrue(group.tile_info_label.text())
        self.assertEqual(group.tile_settings()[:3], (120.0, 15.0, 15.0))

    def test_sent_gcode_log(self):
        log = self.make(SentGcodeLog)
        log.append_lines(["G21", "G1 X1"])
        log.append_lines([])
        log.mark_end(False)
        lines = log.text_edit.toPlainText().splitlines()
        self.assertEqual(lines, ["G21", "G1 X1", tr("queue.sent_log_stopped")])
        log.clear_lines()
        self.assertEqual(log.text_edit.toPlainText(), "")

    def test_realtime_commands(self):
        commands = self.make(RealtimeCommands)
        signals = [
            commands.pause_requested,
            commands.resume_requested,
            commands.reset_requested,
            commands.emergency_stop_requested,
            commands.send_job_requested,
        ]
        received = [record(signal) for signal in signals]
        for button in commands.findChildren(QToolButton):
            button.click()
        self.assertEqual(received, [[()]] * 5)
        commands.set_send_enabled(False)
        self.assertFalse(commands.send_button.isEnabled())

    def test_machine_params_profile_round_trip(self):
        page = self.make(MachineParamsPage)
        page.apply_profile_values(
            {
                "w": 420.0,
                "h": 310.0,
                "focal": 0.08,
                "max_speed": 7000.0,
                "accel": 800.0,
            }
        )
        self.assertEqual(
            page.profile_values(),
            {
                "w": 420.0,
                "h": 310.0,
                "focal": 0.08,
                "max_speed": 7000.0,
                "accel": 800.0,
            },
        )
        page.apply_profile_values({})  # ancien profil : défauts
        values = page.profile_values()
        self.assertEqual(
            (values["w"], values["max_speed"], values["accel"]),
            (420.0, 6000.0, 500.0),
        )

    def test_job_position_profile_round_trip(self):
        box = self.make(JobPositionBox)
        box.apply_profile_values({"origin": "center"})
        self.assertEqual(box.profile_values(), {"origin": "center"})
        box.apply_profile_values({"origin": "Inconnue"})  # gardée
        self.assertEqual(box.profile_values(), {"origin": "center"})

    def test_origin_is_a_code_whatever_the_language(self):
        # Bug : la génération comparait le libellé affiché à « Centre » : en
        # anglais, allemand ou espagnol, l'origine au centre restait sans effet.
        box = self.make(JobPositionBox)
        self.assertEqual(box.origin(), "bottom_left")
        box.origin_combo.setCurrentIndex(1)
        self.assertEqual(box.origin(), "center")
        # Anciens profils / projets : libellé enregistré dans n'importe quelle langue.
        for old_label in ("Bas-Gauche (0,0)", "Bottom-Left (0,0)", "Unten links (0,0)"):
            box.set_origin(old_label)
            self.assertEqual(box.origin(), "bottom_left", old_label)
            box.set_origin("Centre" if old_label.startswith("Bas") else "Center" if old_label.startswith("Bot")
                           else "Mitte")
            self.assertEqual(box.origin(), "center", old_label)


if __name__ == "__main__":
    unittest.main()
