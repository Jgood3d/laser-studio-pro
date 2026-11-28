"""Filtre des avertissements de Qt sans conséquence
(ui.app.qt_messages.qt_message_handler)."""
import contextlib
import io
import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtCore import qInstallMessageHandler, qWarning
    from laser_studio.ui.app import qt_messages
except ImportError:  # PyQt6 manquant
    qt_messages = None


@unittest.skipIf(qt_messages is None, "qt_messages non importable ici")
class QtMessageHandlerTests(unittest.TestCase):
    def emit(self, text):
        err = io.StringIO()
        qInstallMessageHandler(qt_messages.qt_message_handler)
        try:
            with contextlib.redirect_stderr(err):
                qWarning(text)
        finally:
            qInstallMessageHandler(None)
        return err.getvalue()

    def test_wayland_mouse_grab_warning_is_dropped(self):
        self.assertEqual(self.emit(
            "This plugin supports grabbing the mouse only for popup windows"),
            "")

    def test_other_messages_are_still_shown(self):
        self.assertEqual(self.emit("Something else went wrong"),
                         "Something else went wrong\n")


if __name__ == "__main__":
    unittest.main()
