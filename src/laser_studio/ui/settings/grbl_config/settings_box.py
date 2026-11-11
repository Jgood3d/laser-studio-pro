"""Cadre « Réglages GRBL complets ($$) » de la page Configuration GRBL."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from laser_studio.i18n import tr


class GrblSettingsBox(QGroupBox):
    """Texte des réglages GRBL ($$) et ses boutons : lire depuis la
    machine, envoyer, exporter, importer, lier au profil machine.

    Il ne parle pas au graveur : ses boutons émettent des signaux. Le
    texte reste accessible (`text_edit`).
    """

    read_requested = pyqtSignal()
    send_requested = pyqtSignal()
    export_requested = pyqtSignal()
    import_requested = pyqtSignal()
    link_to_profile_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(tr("ui.grbl_settings_box"), parent)
        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(tr("ui.grbl_settings_placeholder"))
        self.text_edit.setMaximumHeight(140)
        self.text_edit.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.text_edit)

        buttons = QHBoxLayout()
        for key, signal in (
            ("ui.grbl_read", self.read_requested),
            ("ui.grbl_send", self.send_requested),
            ("ui.grbl_export", self.export_requested),
            ("ui.grbl_import", self.import_requested),
        ):
            buttons.addWidget(self._button(key, signal))
        layout.addLayout(buttons)
        layout.addWidget(
            self._button(
                "ui.grbl_link_profile", self.link_to_profile_requested
            )
        )
        self.setLayout(layout)

    @staticmethod
    def _button(key, signal):
        button = QPushButton(tr(key))
        button.clicked.connect(signal)
        return button
