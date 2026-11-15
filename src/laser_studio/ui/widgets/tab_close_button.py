"""Petite croix de fermeture, placée sur un seul onglet."""

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QStyle, QToolButton

from laser_studio.i18n import tr


class TabCloseButton(QToolButton):
    """Croix à droite du titre d'un onglet ; émet clicked.

    Pour un onglet fermable parmi d'autres qui ne le sont pas (setTabsClosable
    mettrait une croix sur tous) :

        button = TabCloseButton()
        button.clicked.connect(lambda: actions.gcode_console.setChecked(False))
        tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, button)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton)
        )
        self.setIconSize(QSize(12, 12))
        self.setAutoRaise(True)
        self.setToolTip(tr("ui.close_tab"))
