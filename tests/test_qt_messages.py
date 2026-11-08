<<<<<<< HEAD
"""Filtre des avertissements de Qt sans conséquence
(qt_messages.qt_message_handler)."""
=======
"""Filtre des avertissements de Qt sans conséquence (main.qt_message_handler)."""
>>>>>>> aed42af (feat: description de vos modifications)
import contextlib
import io
import os
import sys
import unittest

<<<<<<< HEAD
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt6.QtCore import qInstallMessageHandler, qWarning
    import qt_messages
except ImportError:  # PyQt6 manquant
    qt_messages = None


@unittest.skipIf(qt_messages is None, "qt_messages non importable ici")
class QtMessageHandlerTests(unittest.TestCase):
    def emit(self, text):
        err = io.StringIO()
        qInstallMessageHandler(qt_messages.qt_message_handler)
=======
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt6.QtCore import qInstallMessageHandler, qWarning
    import main
except ImportError:  # PyQt6 manquant
    main = None


@unittest.skipIf(main is None, "main non importable ici")
class QtMessageHandlerTests(unittest.TestCase):
    def emit(self, text):
        err = io.StringIO()
        qInstallMessageHandler(main.qt_message_handler)
>>>>>>> aed42af (feat: description de vos modifications)
        try:
            with contextlib.redirect_stderr(err):
                qWarning(text)
        finally:
            qInstallMessageHandler(None)
        return err.getvalue()

    def test_wayland_mouse_grab_warning_is_dropped(self):
<<<<<<< HEAD
        self.assertEqual(self.emit(
            "This plugin supports grabbing the mouse only for popup windows"),
            "")

    def test_other_messages_are_still_shown(self):
        self.assertEqual(self.emit("Something else went wrong"),
                         "Something else went wrong\n")
=======
        self.assertEqual(self.emit("This plugin supports grabbing the mouse only for popup windows"), "")

    def test_other_messages_are_still_shown(self):
        self.assertEqual(self.emit("Something else went wrong"), "Something else went wrong\n")
>>>>>>> aed42af (feat: description de vos modifications)


if __name__ == "__main__":
    unittest.main()
