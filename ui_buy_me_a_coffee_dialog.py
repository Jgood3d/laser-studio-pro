"""Boîte de dialogue « Buy me a coffee »."""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from i18n import tr


def show_buy_me_a_coffee_dialog(parent):
    """Boîte de dialogue « Buy me a coffee »."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("ui.coffee_title"))
    layout = QVBoxLayout(dialog)

    lbl_text = QLabel(
        tr("ui.coffee_body").format(
            link='<a href="https://ko-fi.com/jb3dlaser">'
            "ko-fi.com/jb3dlaser</a>"
        )
    )
    lbl_text.setTextFormat(Qt.TextFormat.RichText)
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
