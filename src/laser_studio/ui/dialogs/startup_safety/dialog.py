"""Boîte de dialogue d'avertissement laser au démarrage."""
from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QMessageBox, QWidget

from laser_studio.controllers.startup_safety import REMINDER_EVERY
from laser_studio.i18n import tr


def confirm_startup_safety(
    parent: QWidget | None = None, hide_checked: bool = False
) -> tuple[bool, bool]:
    """Affiche l'avertissement de sécurité, avec une case « Ne plus afficher
    à chaque démarrage » (comme les astuces du jour), cochée si
    `hide_checked`.

    Quand afficher la fenêtre : voir controllers.startup_safety.

    Returns
    -------
    tuple[bool, bool]
        (validé, case cochée) : validé est True si l'utilisateur clique sur
        OK, False s'il annule.
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

    hide_check = QCheckBox(tr("startup.safety.dont_show").format(n=REMINDER_EVERY))
    hide_check.setChecked(hide_checked)
    box.setCheckBox(hide_check)

    accepted = box.exec() == QMessageBox.StandardButton.Ok
    return accepted, hide_check.isChecked()
