"""Boîte de dialogue « À propos »."""

import os
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from app_utils import APP_VERSION, find_resource, get_app_dir, get_bundle_dir
from i18n import tr
from widgets_extra import scaled_to_width_hidpi


def show_about_dialog(parent):
    """Boîte de dialogue « À propos »."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("ui.about_title"))
    layout = QVBoxLayout(dialog)

    banner_path = find_resource("laser_studio_pro_banner.png")
    if banner_path:
        pixmap = QPixmap(banner_path)
        if not pixmap.isNull():
            lbl_banner = QLabel()
            lbl_banner.setPixmap(
                scaled_to_width_hidpi(pixmap, 420, parent.devicePixelRatioF())
            )
            lbl_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl_banner)
        else:
            lbl_banner_missing = QLabel(
                tr("ui.banner_unreadable").format(path=banner_path)
            )
            lbl_banner_missing.setStyleSheet("color: #cc6666;")
            lbl_banner_missing.setWordWrap(True)
            layout.addWidget(lbl_banner_missing)
    else:
        searched = [
            os.path.join(get_app_dir(), "laser_studio_pro_banner.png"),
            os.path.join(get_bundle_dir(), "laser_studio_pro_banner.png"),
        ]
        searched_txt = "\n".join(sorted(set(searched)))
        lbl_banner_missing = QLabel(
            tr("ui.banner_missing").format(paths=searched_txt)
        )
        lbl_banner_missing.setStyleSheet("color: #cc6666;")
        lbl_banner_missing.setWordWrap(True)
        layout.addWidget(lbl_banner_missing)

    lbl_text = QLabel(
        f"<b>Laser Studio Pro</b> — {tr('menu.help.version')} "
        f"{APP_VERSION}<br>" + tr("dialog.about.description")
    )
    lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_text.setWordWrap(True)
    layout.addWidget(lbl_text)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.exec()
