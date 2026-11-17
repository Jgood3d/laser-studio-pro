"""Onglet « Calques » : profils matériaux, liste des calques et de leurs
réglages laser."""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QLabel, QToolBar, QVBoxLayout, QWidget

from laser_studio.i18n import tr
from laser_studio.ui.utils import palette_icon
from laser_studio.ui.widgets import FloatingToolBar
from laser_studio.vector_layers import LayerManagerWidget

# Icône (pack Breeze embarqué) et infobulle de chaque action de la barre, dans
# l'ordre de LayerManagerWidget.layer_actions : ajouter, supprimer, monter,
# descendre.
LAYER_ACTION_ICONS = (
    ("list-add", "layers.add_tip"),
    ("list-remove", "layers.remove_tip"),
    ("go-up", "layers.move_up_tip"),
    ("go-down", "layers.move_down_tip"),
)

# Actions des profils matériaux : (nom du signal, icône, libellé en infobulle).
MATERIAL_ACTIONS = (
    ("new_material_requested", "document-new", "material.new"),
    ("delete_material_requested", "edit-delete", "material.delete"),
    ("export_materials_requested", "document-export", "material.export"),
    ("import_materials_requested", "document-import", "material.import"),
)


class LayersTab(QWidget):
    """Page de l'onglet « Calques ».

    En haut, une barre d'outils des profils matériaux : la liste des
    matériaux (material_combo), puis Nouveau, Supprimer, Exporter et
    Importer. Un matériau mémorise les réglages des calques : en choisir un
    dans la liste émet material_selected, et la fenêtre met le tableau à
    jour. Il n'y a pas de bouton « Enregistrer » : le matériau choisi suit
    chaque changement de calque (MaterialsController.store_current_settings).

    Dessous, la liste des calques (LayerManagerWidget, encore dans
    vector_layers.py), dont elle relaie le signal layers_changed, émis à
    chaque modification d'un calque :

        tab = LayersTab(layer_manager, ["MDF 4mm"], focal_getter=lambda: 0.1)
        tab.layers_changed.connect(self.on_layers_changed)
        tab.material_selected.connect(materials.apply_selected)

    `focal_getter` : fonction qui renvoie la taille du spot du laser, en mm.
    Les calques s'en servent pour leur intervalle de lignes.

    Ajouter / supprimer / monter / descendre un calque : barre flottante
    d'icônes à gauche de la table (actions_toolbar), libellés en infobulle.
    """

    layers_changed = pyqtSignal()
    # Matériau choisi dans la liste PAR L'UTILISATEUR (pas quand la liste est
    # remplie par programme : projet ouvert, profil machine choisi).
    material_selected = pyqtSignal(int)
    new_material_requested = pyqtSignal()
    delete_material_requested = pyqtSignal()
    export_materials_requested = pyqtSignal()
    import_materials_requested = pyqtSignal()

    def __init__(self, layer_manager, material_names=(), focal_getter=None, parent=None):
        super().__init__(parent)
        self.focal_getter = focal_getter
        self.layer_widget = LayerManagerWidget(
            layer_manager, focal_getter=focal_getter
        )
        self.layer_widget.layers_changed.connect(self.layers_changed)
        layout = QVBoxLayout(self)
        layout.addWidget(self._materials_toolbar(material_names))
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

    # -- construction

    def _materials_toolbar(self, material_names):
        """« Profil matériau : [liste] » puis les actions, en icônes."""
        toolbar = QToolBar(tr("material.box_title"), self)
        toolbar.setObjectName("materials_toolbar")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        label = QLabel(tr("material.select"))
        label.setContentsMargins(0, 0, 6, 0)
        toolbar.addWidget(label)
        self.material_combo = QComboBox()
        self.material_combo.setMinimumContentsLength(18)
        self.material_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.material_combo.addItems(list(material_names))
        # activated : choix de l'utilisateur seulement (voir material_selected).
        self.material_combo.activated.connect(self.material_selected)
        toolbar.addWidget(self.material_combo)
        toolbar.addSeparator()
        self.material_actions = {}
        for signal_name, icon, key in MATERIAL_ACTIONS:
            action = toolbar.addAction(palette_icon(icon, self.palette()), tr(key))
            action.setToolTip(tr(key))
            action.triggered.connect(getattr(self, signal_name))
            self.material_actions[signal_name] = action
        return toolbar
