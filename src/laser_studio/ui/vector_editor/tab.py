"""Onglet « Graver une image vectorielle » : en haut, Importer et la grille
magnétique ; le canevas avec sa barre flottante (sélection, créer et
dessiner) ; à droite, la barre d'édition (générateurs compris) contre la
liste des objets (ObjectsPanel), avec les propriétés de la sélection en
dessous (alignement compris, pour plusieurs objets).

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
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QMenu, QSplitter, QStyle, QToolBar, QToolButton, QVBoxLayout,
                             QWidget)

from laser_studio.i18n import tr
from laser_studio.ui.utils import import_button, palette_icon
from laser_studio.ui.vector_editor.empty_hint import EmptyCanvasHint
from laser_studio.ui.vector_editor.objects_panel import ObjectsPanel
from laser_studio.ui.vector_editor.properties_panel import PropertiesWidgets
from laser_studio.ui.vector_editor.shortcuts import with_shortcut
from laser_studio.ui.widgets import FloatingToolBar

# Largeur de la colonne de droite (barre d'édition, liste des objets et propriétés), en px.
SIDE_WIDTH = 420
SIDE_MIN_WIDTH = 330
# Écart entre la poignée du séparateur et la colonne de droite, en px.
SIDE_LEFT_MARGIN = 6
# Barre d'édition, verticale entre le canevas et la liste des objets : (commande, clé du libellé, icône) ;
# None = séparateur. En tête, la fenêtre des générateurs (boîte, puzzle, boule de Noël, porte-clés).
EDIT_ACTIONS = (
    ("generators", "ui.vector_generators", "draw-cuboid"),
    None,
    ("edit", "ui.vector_edit_selection", "document-edit"),
    ("rotate", "ui.vector_rotate_90", "object-rotate-right"),
    ("duplicate", "ui.vector_duplicate", "edit-duplicate"),
    ("serial", "ui.vector_serial_duplicate", "view-grid"),
    ("nesting", "ui.vector_nesting", "object-group"),
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
# Outils plus rares de la barre d'édition, rangés dans un bouton à menu nommé (la barre passe de 19 à 12 icônes) :
# groupe -> (clé du libellé, icône, commandes). Le bouton prend la place du premier outil du groupe.
EDIT_GROUPS = {
    "arrange": ("vector.group_arrange", "view-grid", ("serial", "nesting", "jig")),
    "paths": ("vector.group_paths", "format-node-curve", ("explode", "nodes", "text_follow", "medal")),
}
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
# Alignement, dans les propriétés quand plusieurs objets sont choisis : (commande, clé du libellé) ; None = séparateur.
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
COMMANDS = ("import", "box", "puzzle", "ornament", "keychain") + tuple(
    entry[0] for entry in EDIT_ACTIONS + CREATE_ACTIONS + ALIGN_ACTIONS if entry) + ("library",)


def _grouped(entries, actions, make_menu):
    """Actions de la barre d'édition, celles d'un groupe (EDIT_GROUPS) remplacées par le bouton à menu du groupe,
    à la place de son premier outil ; make_menu(groupe) crée l'action du bouton. None = séparateur."""
    group_of = {name: group for group, (_key, _icon, names) in EDIT_GROUPS.items() for name in names}
    result, menus = [], {}
    for entry, action in zip(entries, actions):
        group = group_of.get(entry[0]) if entry else None
        if group is None:
            result.append(action)
            continue
        if group not in menus:
            menus[group] = make_menu(group)
            result.append(menus[group])
        action.setText(action.toolTip())                # dans un menu, le libellé sans pictogramme
        menus[group].menu().addAction(action)
    return result


def _toolbar(actions):
    """Barre d'outils fixe de `actions` ; None = séparateur."""
    bar = QToolBar()
    for action in actions:
        if action is None:
            bar.addSeparator()
        else:
            bar.addAction(action)
    return bar


class VectorEditorTab(QWidget):
    """`canvas` : VectorCanvasView, placé dans l'onglet sous la rangée des outils."""

    command = pyqtSignal(str)
    draw_tool_requested = pyqtSignal(object)
    camera_background_toggled = pyqtSignal(bool)
    camera_refresh_requested = pyqtSignal()
    vectorize_requested = pyqtSignal()        # « Vectoriser une image » : la fenêtre ouvre l'onglet Vectorisation

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        layout = QVBoxLayout(self)
        # Une seule rangée en haut : marges réduites pour le canevas
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self._toolbars()
        layout.addLayout(self._top_row())
        # Canevas à gauche ; à droite la liste des objets, et sous elle les propriétés de la sélection.
        self.objects_panel = ObjectsPanel()
        self.properties_box = self._properties_box()
        side = QWidget()
        side.setProperty("role", "sidebar")           # panneau latéral (thèmes modernes : plus sombre, à plat)
        side_row = QHBoxLayout(side)
        side_row.setContentsMargins(SIDE_LEFT_MARGIN, 0, 0, 0)
        side_row.setSpacing(4)
        side_row.addWidget(self.edit_toolbar)      # à portée de main, contre la liste des objets
        side_layout = QVBoxLayout()
        side_layout.setSpacing(4)
        side_row.addLayout(side_layout, 1)
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
        # Après le séparateur : la barre flottante est enfant du premier parent du canevas qui n'en est pas un.
        # Sélection en tête : l'outil dont on se sert le plus.
        select, *draw = self.draw_buttons.values()
        self.create_toolbar = FloatingToolBar([select, None, *self._create_actions, None, *draw],
                                              self.canvas, anchor="left")
        self.empty_hint = EmptyCanvasHint(canvas)          # canevas vide : importer, dessiner, bibliothèque
        self.empty_hint.command.connect(
            lambda name: self.vectorize_requested.emit() if name == "vectorize" else self.command.emit(name))

    # -- construction

    def _action(self, text, tooltip, command=None, icon_name=None):
        """Action des barres d'outils : `text`, infobulle `tooltip`, icône Breeze dans la couleur du thème ;
        émet command(`command`) si elle est donnée."""
        action = QAction(text, self)
        action.setToolTip(with_shortcut(tooltip, command))           # le raccourci là où on le cherche
        if icon_name:
            action.setIcon(palette_icon(icon_name, self.palette()))
        if command is not None:
            action.triggered.connect(lambda _checked=False, name=command: self.command.emit(name))
        return action

    def _group_action(self, group):
        """Bouton à menu d'un groupe d'outils (EDIT_GROUPS) : icône, libellé en infobulle, menu titré."""
        key, icon, _names = EDIT_GROUPS[group]
        action = self._action(tr(key), tr(f"{key}_tip"), icon_name=icon)
        action.setMenu(QMenu(tr(key), self))
        self.group_actions[group] = action
        return action

    @staticmethod
    def _actions(entries, make):
        """Actions d'une barre d'outils : make(*entrée) pour chaque entrée, None (séparateur) gardé tel quel."""
        return [make(*entry) if entry else None for entry in entries]

    def _top_row(self):
        """Importer, puis la grille magnétique à droite. Le plein écran est celui de la barre d'outils
        principale."""
        row = QHBoxLayout()
        row.setSpacing(4)
        # Même gros bouton que « Charger Image » ; un SVG / DXF déposé dessus est importé (dropEvent de la fenêtre).
        button = import_button(tr("ui.vector_import_drop"), palette_icon("document-import", self.palette()))
        button.setToolTip(tr("ui.vector_import_svg"))
        button.clicked.connect(lambda: self.command.emit("import"))
        row.addWidget(button)
        # À côté : une image bitmap à transformer d'abord en dessin (onglet « Vectorisation d'image »).
        vectorize = import_button(tr("ui.vector_vectorize"), palette_icon("draw-bezier-curves", self.palette()))
        vectorize.setToolTip(tr("ui.vector_vectorize_tip"))
        vectorize.clicked.connect(lambda: self.vectorize_requested.emit())
        row.addWidget(vectorize)
        self.top_buttons = {"import": button, "vectorize": vectorize}
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

    def _toolbars(self):
        # Édition de la sélection : barre d'icônes, le libellé en infobulle.
        edit_actions = self._actions(EDIT_ACTIONS, lambda name, key, icon: self._action(
            tr(key), tr(key).lstrip("↻↶↷🧩 "), name, icon))
        edit_actions[0].setToolTip(tr("ui.vector_generators_tip"))
        self.edit_actions = {entry[0]: action for entry, action in zip(EDIT_ACTIONS, edit_actions) if entry}
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
        self._create_actions = create_actions
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
        # Édition : colonne d'icônes contre la liste des objets ; ce qui ne tient pas passe dans le menu ».
        self.group_actions = {}
        self.edit_toolbar = _toolbar(_grouped(EDIT_ACTIONS, edit_actions, self._group_action))
        self.edit_toolbar.setOrientation(Qt.Orientation.Vertical)
        self.edit_toolbar.setIconSize(QSize(20, 20))
        for group in self.group_actions.values():          # un clic ouvre le menu (pas d'action par défaut)
            self.edit_toolbar.widgetForAction(group).setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.align_toolbar = _toolbar(align_actions)
        self.align_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        # Pictogrammes plus grands que le texte courant, pour rester lisibles.
        self.align_toolbar.setStyleSheet("QToolButton { font-size: 16px; padding: 2px 2px; }")
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
        label.setStyleSheet("color: palette(placeholder-text); font-size: 12px;")
        form.addWidget(label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)
        x, y, rotation = (self._spin(-1000.0, 1000.0, 2, 110), self._spin(-1000.0, 1000.0, 2, 110),
                          self._spin(-360.0, 360.0, 1, 110))
        layer = QComboBox()
        layer.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)   # « Gravure [Gravure Remplie] » entier
        for row, (key, widget) in enumerate((("ui.vector_x_mm", x), ("ui.vector_y_mm", y),
                                              ("ui.vector_rotation_deg", rotation), ("ui.vector_layer", layer))):
            grid.addWidget(QLabel(tr(key)), row, 0)
            # Champs alignés : leur largeur maximale (110 px) ne plafonne plus la colonne, la liste des calques
            # y prend la largeur de son texte.
            if widget is layer:
                grid.addWidget(widget, row, 1)
            else:
                grid.addWidget(widget, row, 1, Qt.AlignmentFlag.AlignLeft)
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
        self.align_toolbar.setVisible(False)
        form.addWidget(self.align_toolbar)

        box.setEnabled(False)
        box.setVisible(False)
        self.properties_widgets = PropertiesWidgets(
            label=label, box=box, x=x, y=y, rotation=rotation, layer=layer, size_row=size_row,
            width=width, height=height, anchor_lock=anchor_lock, anchor=anchor, align_row=self.align_toolbar)
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
