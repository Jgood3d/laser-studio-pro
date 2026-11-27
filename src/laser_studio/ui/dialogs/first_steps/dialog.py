"""Fenêtre « Premiers pas » : les quatre étapes de FirstStepsController (controllers/first_steps.py), chacune
avec son explication, son bouton et son état (« Fait » écrit en toutes lettres, pas seulement une couleur).

    dialog = open_first_steps(window, steps)      # non modale, une seule à la fois
"""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QPushButton,
                             QVBoxLayout)

from laser_studio.controllers.first_steps import STEPS
from laser_studio.i18n import tr


class FirstStepsDialog(QDialog):
    """Signaux : step_requested(clé), show_at_launch_changed(bool). `set_done({clé: fait})` met les états
    à jour."""

    step_requested = pyqtSignal(str)
    show_at_launch_changed = pyqtSignal(bool)

    def __init__(self, show_at_launch=True, parent=None):
        super().__init__(parent)
        self.setObjectName("first_steps_dialog")
        self.setWindowTitle(tr("first_steps.title"))
        layout = QVBoxLayout(self)
        intro = QLabel(tr("first_steps.intro"))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        grid = QGridLayout()
        self.buttons, self.states = {}, {}
        for row, key in enumerate(STEPS):
            text = QLabel(f"<b>{row + 1}. {tr(f'first_steps.{key}')}</b><br>{tr(f'first_steps.{key}_help')}")
            text.setWordWrap(True)
            button = QPushButton(tr(f"first_steps.{key}_button"))
            button.clicked.connect(lambda _checked=False, key=key: self.step_requested.emit(key))
            state = QLabel()
            grid.addWidget(text, row, 0)
            grid.addWidget(button, row, 1)
            grid.addWidget(state, row, 2)
            self.buttons[key], self.states[key] = button, state
        grid.setColumnStretch(0, 1)
        layout.addLayout(grid)
        self.show_check = QCheckBox(tr("first_steps.show_at_launch"))
        self.show_check.setChecked(show_at_launch)
        self.show_check.toggled.connect(self.show_at_launch_changed)
        layout.addWidget(self.show_check)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.close)
        layout.addWidget(close)
        self.setMinimumWidth(720)                    # explications sur deux lignes, boutons entiers

    def showEvent(self, event):
        """Hauteur ajustée aux explications sur plusieurs lignes, une fois le thème appliqué (sans cela, la
        fenêtre gardait la hauteur calculée pour une largeur plus étroite)."""
        super().showEvent(event)
        self.resize(self.width(), self.layout().heightForWidth(self.width()))

    def set_done(self, done):
        for key, state in self.states.items():
            state.setText(tr("first_steps.done") if done.get(key) else tr("first_steps.todo"))


def open_first_steps(parent, steps):
    """Ouvre (ou ramène devant) la fenêtre « Premiers pas » branchée sur `steps` (FirstStepsController)."""
    dialog = parent.findChild(FirstStepsDialog) if parent is not None else None
    if dialog is None:
        dialog = FirstStepsDialog(steps.should_show_at_launch(), parent)
        dialog.step_requested.connect(steps.run)
        dialog.show_at_launch_changed.connect(steps.set_show_at_launch)
        steps.changed.connect(lambda: dialog.set_done(steps.done()))
        dialog.set_done(steps.done())
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog
