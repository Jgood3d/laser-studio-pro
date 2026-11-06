"""Boîte de dialogue « Support »."""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from i18n import tr


def show_support_dialog(parent):
    """Boîte de dialogue « Support »."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("ui.support_title"))
    layout = QVBoxLayout(dialog)

    lbl_text = QLabel(tr("ui.support_body"))
    lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_text.setWordWrap(True)
    lbl_text.setOpenExternalLinks(True)
    lbl_text.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextBrowserInteraction
    )
    layout.addWidget(lbl_text)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.exec()
