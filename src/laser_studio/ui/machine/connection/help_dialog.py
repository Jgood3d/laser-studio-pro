"""Aide « Port introuvable ? » du panneau Connexion."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from laser_studio.i18n import tr


def port_help_dialog(parent=None):
    """Boîte d'aide sur les pilotes USB du graveur (CH340, CP210x, FTDI) et le
    groupe « dialout » sous Linux. Les liens s'ouvrent dans le navigateur.

        port_help_dialog(window).exec()
    """
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(tr("usb.help_title"))
    box.setTextFormat(Qt.TextFormat.RichText)
    box.setText(tr("usb.driver_hint"))
    box.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    return box
