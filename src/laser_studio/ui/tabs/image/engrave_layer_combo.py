"""Liste « Calque de gravure » de l'onglet « Graver une image »."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import QComboBox

from laser_studio.i18n import tr

# Mode des calques qui peuvent graver une image (même valeur que dans vector_layers).
ENGRAVE_MODE = "Gravure Remplie"


def _swatch(color):
    """Petit carré de la couleur du calque, comme dans la table des calques."""
    pixmap = QPixmap(12, 12)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


class EngraveLayerComboBox(QComboBox):
    """Calque dont la vitesse et la puissance servent à graver l'image.

    Elle ne liste que les calques en mode gravure (la gravure d'image n'a pas de sens sur un calque de
    découpe) et n'émet `layer_selected(id)` que sur un choix de l'utilisateur, jamais quand la fenêtre
    la remplit (comme MaterialComboBox) :

        combo = EngraveLayerComboBox()
        combo.layer_selected.connect(self._on_engrave_layer_chosen)
        combo.set_layers(layer_manager.layers, current_id)
    """

    layer_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setToolTip(tr("img.engrave_layer_tip"))
        # Les noms de calque peuvent être longs : largeur minimale courte, liste ouverte assez large.
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(12)
        self.activated.connect(self._on_activated)
        self.set_layers([], None)

    def set_layers(self, layers, current_id):
        """Remplit la liste avec les calques en mode gravure de `layers` (objets avec id, name, color,
        mode) et sélectionne `current_id`. Sans lui, le premier calque de gravure est affiché : c'est
        celui que la génération prendra. Sans calque de gravure, la liste est vide et désactivée."""
        engrave = [layer for layer in layers if layer.mode == ENGRAVE_MODE]
        blocked = self.blockSignals(True)
        try:
            self.clear()
            for layer in engrave:
                self.addItem(_swatch(layer.color), layer.name, layer.id)
                self.setItemData(self.count() - 1, layer.name, Qt.ItemDataRole.ToolTipRole)
            if engrave:
                index = self.findData(current_id)
                self.setCurrentIndex(index if index >= 0 else 0)
            else:
                self.addItem(tr("img.engrave_layer_none"), None)
            self.setEnabled(bool(engrave))
        finally:
            self.blockSignals(blocked)
        popup = self.view()
        popup.setMinimumWidth(popup.sizeHintForColumn(0) + 24)

    def layer_id(self):
        """Identifiant du calque affiché, ou None s'il n'y en a pas."""
        return self.currentData()

    def _on_activated(self, index):
        layer_id = self.itemData(index)
        if layer_id is not None:
            self.layer_selected.emit(layer_id)
