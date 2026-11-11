"""Onglet « Vectorisation d'image » (PNG / JPEG -> SVG)."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from laser_studio.ui.tabs.png2svg.widget import PngToSvgWidget
from laser_studio.ui.widgets import TabToolBar


class Png2SvgTab(QWidget):
    """Barre d'outils (plein écran) au-dessus du widget de conversion.

    Le widget de conversion (`converter`) convertit l'image en mémoire ;
    l'onglet relaie ses demandes :

        tab = Png2SvgTab()
        tab.send_to_vector_requested.connect(png2svg.send_to_vector_editor)
        tab.image_changed.connect(self.update_image_actions_state)
    """

    # Texte du SVG généré, à ajouter à l'éditeur vectoriel.
    send_to_vector_requested = pyqtSignal(str)
    # Une image a été chargée ou retirée.
    image_changed = pyqtSignal()
    fullscreen_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = TabToolBar(self)
        toolbar.fullscreen_requested.connect(self.fullscreen_requested)
        self._fullscreen_control = toolbar.fullscreen_action
        layout.addWidget(toolbar)

        self.converter = PngToSvgWidget()
        self.converter.sendToVectorEditor.connect(
            self.send_to_vector_requested
        )
        self.converter.imageChanged.connect(self.image_changed)
        layout.addWidget(self.converter)
