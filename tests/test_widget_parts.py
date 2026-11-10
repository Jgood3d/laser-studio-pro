"""Morceaux d'interface sortis des pages et panneaux : GrblSettingsBox,
ImageTestGroup, SentGcodeLog, RealtimeCommands."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from PIL import Image
    from PyQt6.QtWidgets import QApplication, QPushButton, QToolButton
    from i18n import tr
    from ui.machine.controls.realtime_commands import RealtimeCommands
    from ui.settings.grbl_config.settings_box import GrblSettingsBox
    from ui.settings.test_matrix.image_test_group import ImageTestGroup
    from ui.tabs.job_queue.sent_gcode_log import SentGcodeLog
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


if __name__ == "__main__":
    unittest.main()
