"""Onglet « Calques » : liste des calques et de leurs réglages laser."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.utils import palette_icon
from laser_studio.ui.widgets import FloatingToolBar

# Icône (pack Breeze embarqué) et infobulle de chaque action de la barre, dans
# l'ordre de LayerManagerWidget.layer_actions : ajouter, supprimer, monter,
# descendre.
LAYER_ACTION_ICONS = (
    ("list-add", "layers.add_tip"),
    ("list-remove", "layers.remove_tip"),
    ("go-up", "layers.move_up_tip"),
    ("go-down", "layers.move_down_tip"),
)
from laser_studio.vector_layers import LayerManagerWidget


class LayersTab(QWidget):
    """Page de l'onglet « Calques ».

    Elle enveloppe la liste des calques (LayerManagerWidget, encore dans
    vector_layers.py) et relaie son signal layers_changed, émis à chaque
    modification d'un calque :

        tab = LayersTab(layer_manager, focal_getter=lambda: 0.1)
        tab.layers_changed.connect(self.on_layers_changed)

    `focal_getter` : fonction qui renvoie la taille du spot du laser, en mm.
    Les calques s'en servent pour leur intervalle de lignes.

    Ajouter / supprimer / monter / descendre un calque : barre flottante
    d'icônes à gauche de la table (actions_toolbar), libellés en infobulle.
    """

    layers_changed = pyqtSignal()

    def __init__(self, layer_manager, focal_getter=None, parent=None):
        super().__init__(parent)
        self.focal_getter = focal_getter
        self.layer_widget = LayerManagerWidget(
            layer_manager, focal_getter=focal_getter
        )
        self.layer_widget.layers_changed.connect(self.layers_changed)
        layout = QVBoxLayout(self)
        layout.addWidget(self.layer_widget)
        for action, (icon, tip_key) in zip(
            self.layer_widget.layer_actions, LAYER_ACTION_ICONS
        ):
            action.setIcon(palette_icon(icon, self.palette()))
            action.setToolTip(tr(tip_key))
        self.actions_toolbar = FloatingToolBar(
            self.layer_widget.layer_actions,
            self.layer_widget.table,
            anchor="left",
        )

    # -- état reçu de la fenêtre / du contrôleur

    def refresh(self):
        """Reconstruit la liste après un changement des calques."""
        self.layer_widget.refresh()

    def refresh_focal_quality(self):
        """Met à jour l'indication de qualité après un changement de spot."""
        self.layer_widget.refresh_focal_quality()

    def link_all_to_focal(self):
        """Recalcule l'intervalle de lignes de chaque calque lié au spot."""
        self.layer_widget.link_all_to_focal()
