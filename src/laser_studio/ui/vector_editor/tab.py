"""Onglet « Graver une image vectorielle » : boutons des outils, canevas avec
ses barres flottantes (créer et dessiner, édition, alignement) et, à droite,
la liste des objets (ObjectsPanel) avec les propriétés de la sélection en
dessous.

    tab = VectorEditorTab(canvas)
    tab.command.connect(lambda name: commands[name]())      # "rotate", "align_left"...
    tab.draw_tool_requested.connect(editor.choose_draw_tool)
    editor.draw_tool_changed.connect(tab.show_draw_tool)

C'est une vue : chaque bouton émet `command(nom)` (noms dans COMMANDS),
les outils de la souris `draw_tool_requested(outil)`, l'interrupteur « Fond
caméra » `camera_background_toggled(actif)` et son bouton « Actualiser »
`camera_refresh_requested()` ; la grille magnétique
règle le canevas directement. Le panneau des propriétés
(VectorPropertiesPanel) remplit `properties_widgets` ; la liste des objets
(`objects_panel`) émet ses propres signaux.
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QPushButton, QSplitter, QStyle, QVBoxLayout, QWidget)

from laser_studio.i18n import tr
from laser_studio.ui.utils import palette_icon
from laser_studio.ui.vector_editor.objects_panel import ObjectsPanel
from laser_studio.ui.vector_editor.properties_panel import PropertiesWidgets
from laser_studio.ui.widgets import FloatingToolBar

# Largeur de la colonne de droite (liste des objets et propriétés), en px.
SIDE_WIDTH = 380
SIDE_MIN_WIDTH = 280
# Écart entre la poignée du séparateur et la colonne de droite, en px.
SIDE_LEFT_MARGIN = 6
# Rangée du haut : (commande, clé du libellé, clé de l'infobulle ou None, icône Breeze).
TOP_BUTTONS = (
    ("import", "ui.vector_import_svg", None, "document-import"),
    ("box", "ui.vector_box_generator", "ui.vector_box_generator_tip", "draw-cuboid"),
    ("puzzle", "ui.vector_puzzle_generator", "ui.vector_puzzle_generator_tip", "games-config-board"),
    ("ornament", "ui.vector_ornament_generator", "ui.vector_ornament_generator_tip", "draw-ellipse"),
    ("keychain", "ui.vector_keychain_generator", "ui.vector_keychain_generator_tip", "keychain"),
    ("nesting", "ui.vector_nesting", "ui.vector_nesting_tip", "object-group"),
)
# Barre d'édition, en haut du canevas : (commande, clé du libellé, icône) ; None = séparateur.
EDIT_ACTIONS = (
    ("edit", "ui.vector_edit_selection", "document-edit"),
    ("rotate", "ui.vector_rotate_90", "object-rotate-right"),
    ("duplicate", "ui.vector_duplicate", "edit-duplicate"),
    ("serial", "ui.vector_serial_duplicate", "view-grid"),
    ("jig", "ui.vector_jig", "draw-rectangle"),
    ("delete", "ui.vector_delete", "edit-delete"),
    ("delete_all", "ui.vector_delete_all", "edit-clear-all"),
    None,
    ("explode", "vector.explode_path", "object-ungroup"),
    ("nodes", "vector.edit_nodes", "format-node-curve"),
    ("text_follow", "vector.text_follow", "text-follow-path"),
    ("medal", "vector.medal", "insert-text"),
    None,
    ("undo", "ui.vector_undo", "edit-undo"),
    ("redo", "ui.vector_redo", "edit-redo"),
    None,
    ("zoom_in", "ui.vector_zoom_in", "zoom-in"),
    ("zoom_out", "ui.vector_zoom_out", "zoom-out"),
)
# Barre de gauche : ajouter un objet, puis la bibliothèque de modèles.
CREATE_ACTIONS = (
    ("text", "ui.vector_add_text", "insert-text"),
    ("shape", "ui.vector_add_shape", "shape-choose"),
)
# Outils de la souris (un seul coché à la fois) : (outil, clé du libellé, icône).
DRAW_TOOLS = (
    (None, "ui.vector_tool_select", "tool-pointer"),
    ("line", "ui.vector_tool_line", "draw-line"),
    ("rect", "ui.vector_tool_rect", "draw-rectangle"),
    ("circle", "ui.vector_tool_circle", "draw-circle"),
    ("ellipse", "ui.vector_tool_ellipse", "draw-ellipse"),
    ("measure", "ui.vector_tool_measure", "measure"),
)
# Barre d'alignement, à droite du canevas : (commande, clé du libellé) ; None = séparateur.
ALIGN_ACTIONS = (
    ("align_left", "ui.vector_align_left"),
    ("align_center_h", "ui.vector_align_center_h"),
    ("align_right", "ui.vector_align_right"),
    None,
    ("align_top", "ui.vector_align_top"),
    ("align_middle_v", "ui.vector_align_middle_v"),
    ("align_bottom", "ui.vector_align_bottom"),
    None,
    ("distribute_h", "ui.vector_distribute_h"),
    ("distribute_v", "ui.vector_distribute_v"),
)
# Toutes les commandes émises par l'onglet.
COMMANDS = tuple(name for name, *_ in TOP_BUTTONS) + tuple(
    entry[0] for entry in EDIT_ACTIONS + CREATE_ACTIONS + ALIGN_ACTIONS if entry) + ("library",)


class VectorEditorTab(QWidget):
    """`canvas` : VectorCanvasView, placé dans l'onglet sous la rangée des outils."""

    command = pyqtSignal(str)
    draw_tool_requested = pyqtSignal(object)
    camera_background_toggled = pyqtSignal(bool)
    camera_refresh_requested = pyqtSignal()

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        layout = QVBoxLayout(self)
        # Une seule rangée en haut : marges réduites pour le canevas
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addLayout(self._top_row())
        # Canevas à gauche ; à droite la liste des objets, et sous elle les propriétés de la sélection.
        self.objects_panel = ObjectsPanel()
        self.properties_box = self._properties_box()
        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(SIDE_LEFT_MARGIN, 0, 0, 0)
        side_layout.setSpacing(4)
        objects_box = QGroupBox(tr("objects.box"))
        objects_layout = QVBoxLayout(objects_box)
        objects_layout.setContentsMargins(4, 4, 4, 4)
        objects_layout.addWidget(self.objects_panel)
        side_layout.addWidget(objects_box, 1)
        side_layout.addWidget(self.properties_box)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(canvas)
        self.splitter.addWidget(side)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setChildrenCollapsible(False)
        side.setMinimumWidth(SIDE_MIN_WIDTH)
        self.splitter.setSizes([100000, SIDE_WIDTH])
        layout.addWidget(self.splitter, 1)  # stretch: occupe l'espace restant
        self._floating_toolbars()

    # -- construction

    def _action(self, text, tooltip, command=None, icon_name=None):
        """Action des barres flottantes : `text`, infobulle `tooltip`, icône Breeze dans la couleur du thème ;
        émet command(`command`) si elle est donnée."""
        action = QAction(text, self)
        action.setToolTip(tooltip)
        if icon_name:
            action.setIcon(palette_icon(icon_name, self.palette()))
        if command is not None:
            action.triggered.connect(lambda _checked=False, name=command: self.command.emit(name))
        return action

    @staticmethod
    def _actions(entries, make):
        """Actions d'une barre flottante : make(*entrée) pour chaque entrée, None (séparateur) gardé tel quel."""
        return [make(*entry) if entry else None for entry in entries]

    def _top_row(self):
        """Importer et outils (boîte, puzzle, boule de Noël, porte-clés, imbrication), puis la grille
        magnétique à droite. Le plein écran est celui de la barre d'outils principale."""
        row = QHBoxLayout()
        row.setSpacing(4)
        self.top_buttons = {}
        for name, key, tip, icon in TOP_BUTTONS:
            button = QPushButton(tr(key))
            if tip:
                button.setToolTip(tr(tip))
            button.setIcon(palette_icon(icon, self.palette()))
            # L'emoji du libellé (📥, 📦, 🧩) ferait doublon avec l'icône.
            label = button.text()
            if label and not label[0].isalnum():
                button.setText(label.split(" ", 1)[-1])
            button.clicked.connect(lambda _checked=False, n=name: self.command.emit(n))
            row.addWidget(button)
            self.top_buttons[name] = button
        self.top_buttons["import"].setStyleSheet("background-color: #3a6b3a; color: white;")
        row.addStretch()
        self.snap_check = QCheckBox(tr("ui.vector_snap_enable"))
        self.snap_check.toggled.connect(self.canvas.set_snap_enabled)
        row.addWidget(self.snap_check)
        self.snap_step_spin = QDoubleSpinBox()
        self.snap_step_spin.setRange(0.1, 100.0)
        self.snap_step_spin.setValue(5.0)
        self.snap_step_spin.setSuffix(" mm")
        self.snap_step_spin.valueChanged.connect(self.canvas.set_snap_step)
        row.addWidget(self.snap_step_spin)
        return row

    def _floating_toolbars(self):
        # Édition de la sélection : barre d'icônes en haut du canevas, le libellé en infobulle.
        edit_actions = self._actions(EDIT_ACTIONS, lambda name, key, icon: self._action(
            tr(key), tr(key).lstrip("↻↶↷ "), name, icon))
        # Créer et dessiner : texte et forme ajoutent un objet, la bibliothèque aussi ; les outils de la souris
        # sont cochables, un seul à la fois (show_draw_tool).
        create_actions = [self._action(tr(key), tr(key).lstrip("+ "), name, icon) for name, key, icon in CREATE_ACTIONS]
        create_actions.append(self._action(tr("ui.vector_library"), tr("ui.vector_library_tip"), "library",
                                           "view-app-grid"))
        # Fond caméra : interrupteur (capture et affiche l'image de la caméra sous la grille, pour placer le
        # travail sur la vraie matière) et bouton pour la recapturer, sans passer par la fenêtre Caméra.
        self.camera_toggle = QAction(tr("ui.vector_camera_toggle"), self)
        self.camera_toggle.setToolTip(tr("ui.vector_camera_toggle_tip"))
        self.camera_toggle.setIcon(palette_icon("camera-photo", self.palette(),
                                                self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)))
        self.camera_toggle.setCheckable(True)
        self.camera_toggle.toggled.connect(self.camera_background_toggled.emit)
        camera_refresh = self._action(tr("ui.vector_camera_refresh"), tr("ui.vector_camera_refresh_tip"),
                                      icon_name="view-refresh")
        camera_refresh.triggered.connect(lambda _checked=False: self.camera_refresh_requested.emit())
        create_actions += [self.camera_toggle, camera_refresh]
        self.draw_buttons = {}
        for tool, key, icon in DRAW_TOOLS:
            action = self._action(tr(key), f"{tr(key)} — {tr(key + '_tip')}", icon_name=icon)
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, t=tool: self.draw_tool_requested.emit(t))
            self.draw_buttons[tool] = action
        self.draw_buttons[None].setChecked(True)
        # Alignement / répartition : le bouton ne garde que le pictogramme du libellé (« ⊢ ») ; l'infobulle
        # dit l'action (« Aligner à gauche »).
        align_actions = self._actions(ALIGN_ACTIONS, lambda name, key: self._action(
            tr(key).split(" ", 1)[0], tr(f"{key}_tip"), name))
        self.create_toolbar = FloatingToolBar([*create_actions, None, *self.draw_buttons.values()],
                                              self.canvas, anchor="left")
        self.edit_toolbar = FloatingToolBar(edit_actions, self.canvas, top_margin=8)
        self.align_toolbar = FloatingToolBar(align_actions, self.canvas, anchor="right",
                                             button_style=Qt.ToolButtonStyle.ToolButtonTextOnly)
        # Pictogrammes plus grands que le texte courant, pour rester lisibles.
        self.align_toolbar.setStyleSheet(self.align_toolbar.styleSheet()
                                         + " QToolButton { font-size: 16px; min-width: 24px; }")
        self.align_toolbar.setToolTip(tr("ui.vector_align_box"))

    def _properties_box(self):
        """Propriétés de la sélection, sous la liste des objets : description, position, rotation, calque ;
        taille et ancrage (formes seulement). Masquées sans sélection ; remplies par VectorPropertiesPanel."""
        box = QGroupBox(tr("ui.selection_props_box"))
        form = QVBoxLayout(box)
        form.setContentsMargins(8, 6, 8, 6)
        form.setSpacing(4)

        label = QLabel(tr("ui.no_selection_label"))
        label.setWordWrap(True)
        label.setStyleSheet("color: #9aa3b5; font-size: 12px;")
        form.addWidget(label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)
        x, y, rotation = (self._spin(-1000.0, 1000.0, 2, 110), self._spin(-1000.0, 1000.0, 2, 110),
                          self._spin(-360.0, 360.0, 1, 110))
        layer = QComboBox()
        for row, (key, widget) in enumerate((("ui.vector_x_mm", x), ("ui.vector_y_mm", y),
                                              ("ui.vector_rotation_deg", rotation), ("ui.vector_layer", layer))):
            grid.addWidget(QLabel(tr(key)), row, 0)
            grid.addWidget(widget, row, 1)
        grid.setColumnStretch(1, 1)
        form.addLayout(grid)

        # Taille + ancrage (masqués pour texte / SVG / groupe)
        size_row = QWidget()
        size = QGridLayout(size_row)
        size.setContentsMargins(0, 0, 0, 0)
        size.setHorizontalSpacing(6)
        size.setVerticalSpacing(4)
        width, height = self._spin(0.05, 5000.0, 2, 110, " mm"), self._spin(0.05, 5000.0, 2, 110, " mm")
        size.addWidget(QLabel(tr("ui.vector_width_mm")), 0, 0)
        size.addWidget(width, 0, 1)
        size.addWidget(QLabel(tr("ui.vector_height_mm")), 1, 0)
        size.addWidget(height, 1, 1)
        anchor_lock = QCheckBox(tr("ui.vector_anchor_lock"))
        anchor_lock.setChecked(True)
        anchor_lock.setToolTip(tr("ui.vector_anchor_lock_tip"))
        size.addWidget(anchor_lock, 2, 0, 1, 2)
        size.addWidget(QLabel(tr("ui.vector_anchor")), 3, 0)
        anchor = QComboBox()
        for anchor_id, key in (("origin", "ui.vector_anchor_origin"), ("bl", "ui.vector_anchor_bl"),
                               ("br", "ui.vector_anchor_br"), ("tl", "ui.vector_anchor_tl"),
                               ("tr", "ui.vector_anchor_tr")):
            anchor.addItem(tr(key), anchor_id)
        anchor.setCurrentIndex(0)
        anchor.setToolTip(tr("ui.vector_anchor_tip"))
        size.addWidget(anchor, 3, 1)
        size.setColumnStretch(1, 1)
        size_row.setVisible(False)
        form.addWidget(size_row)

        box.setEnabled(False)
        box.setVisible(False)
        self.properties_widgets = PropertiesWidgets(
            label=label, box=box, x=x, y=y, rotation=rotation, layer=layer, size_row=size_row,
            width=width, height=height, anchor_lock=anchor_lock, anchor=anchor)
        return box

    @staticmethod
    def _spin(low, high, decimals, max_width, suffix=""):
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setDecimals(decimals)
        if suffix:
            spin.setSuffix(suffix)
        spin.setMaximumWidth(max_width)
        return spin

    # -- état

    def show_camera_background(self, shown):
        """Coche ou décoche l'interrupteur « Fond caméra », sans émettre de demande."""
        blocked = self.camera_toggle.blockSignals(True)
        self.camera_toggle.setChecked(shown)
        self.camera_toggle.blockSignals(blocked)

    def show_draw_tool(self, tool):
        """Coche le bouton de l'outil de la souris `tool` (None : sélection), sans émettre de demande."""
        for key, action in self.draw_buttons.items():
            blocked = action.blockSignals(True)
            action.setChecked(key == tool)
            action.blockSignals(blocked)
