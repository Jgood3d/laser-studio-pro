"""Boîte de dialogue d'avertissement laser au démarrage."""
from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox, QWidget

from laser_studio.i18n import tr


def confirm_startup_safety(parent: QWidget | None = None) -> bool:
    """Affiche l'avertissement de sécurité.

    Returns
    -------
    bool
        True si l'utilisateur valide (OK), False s'il annule.
    """
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr("startup.safety.title"))
    box.setText(tr("startup.safety.body"))
    box.setInformativeText(tr("startup.safety.detail"))
    box.setStandardButtons(
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
    )
    box.setDefaultButton(QMessageBox.StandardButton.Ok)

    ok_btn = box.button(QMessageBox.StandardButton.Ok)
    cancel_btn = box.button(QMessageBox.StandardButton.Cancel)
    if ok_btn is not None:
        ok_btn.setText(tr("startup.safety.ok"))
    if cancel_btn is not None:
        cancel_btn.setText(tr("startup.safety.cancel"))

    return box.exec() == QMessageBox.StandardButton.Ok
