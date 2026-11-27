"""Aide › Rejoindre la communauté WhatsApp : entrée du menu, QR code et lien cliquable."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from PyQt6.QtWidgets import QApplication
    from laser_studio.i18n import tr
    from laser_studio.ui.app.menu import AppActions
    from laser_studio.ui.app.menu.help_menu import HelpMenu
    from laser_studio.ui.community import COMMUNITY_URL, CommunityDialog
except ImportError:  # PyQt6 manquant
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt6 non importable ici")
class CommunityDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_help_menu_entry_emits_its_signal(self):
        actions = AppActions()
        menu = HelpMenu(actions)
        self.assertIn(actions.community, menu.actions())
        self.assertEqual(actions.community.text(), tr("menu.help.community"))
        received = []
        actions.community_requested.connect(lambda: received.append(True))
        actions.community.trigger()
        self.assertEqual(received, [True])

    def test_dialog_shows_qr_code_and_clickable_link(self):
        dialog = CommunityDialog()
        self.assertFalse(dialog.qr_label.pixmap().isNull())
        self.assertIn(f'href="{COMMUNITY_URL}"', dialog.link_label.text())
        self.assertTrue(dialog.link_label.openExternalLinks())


if __name__ == "__main__":
    unittest.main()
