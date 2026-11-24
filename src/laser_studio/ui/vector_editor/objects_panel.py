"""Liste des objets de l'éditeur vectoriel (ObjectsPanel), à droite du canevas, à la manière de
l'outliner de Blender : du dessus de la pile vers le dessous, un groupe déplié montre ses objets. Devant
chaque objet du dessus de la pile, un œil le masque à l'affichage ; au bout de chaque ligne, « X » le met
sur le calque « Ignoré » (ni gravé ni découpé) ou lui rend son calque, et la poubelle le supprime.

Simple vue : elle affiche ce qu'on lui donne (show_objects, show_selection) et émet des signaux quand
l'utilisateur agit ; le contrôleur de l'éditeur modifie le document.

    panel = ObjectsPanel()
    panel.selection_requested.connect(canvas.select_objects)
    panel.move_requested.connect(editor.move_objects)
    document.order_changed.connect(lambda: panel.show_objects(document.objects, layers.get))
"""
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QMenu, QToolButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from laser_studio.i18n import tr
from laser_studio.models.vector_objects import GroupObject, ShapeObject, SvgPathObject, TextObject
from laser_studio.ui.utils import painted_icon, palette_icon
from laser_studio.vector import boolean_ops

# Colonnes : œil, laser (gravé ou ignoré), nom, calque, poubelle.
EYE_COLUMN, IGNORE_COLUMN, NAME_COLUMN, LAYER_COLUMN, DELETE_COLUMN = range(5)
# Couleur du calque « Ignoré » dans la liste.
IGNORED_COLOR = "#7a7a7a"
OBJECT_ROLE = Qt.ItemDataRole.UserRole
PARENT_ROLE = Qt.ItemDataRole.UserRole + 1     # groupe qui contient l'objet (None en haut de la pile)
TOP_ROLE = Qt.ItemDataRole.UserRole + 2        # objet du document qui le contient (lui-même en haut)
# Longueur maximale d'un texte affiché dans la liste.
MAX_TEXT_CHARS = 28


def object_label(obj):
    """Nom affiché : celui donné par l'utilisateur, sinon ce qu'est l'objet."""
    name = (getattr(obj, "name", "") or "").strip()
    if name:
        return name
    if isinstance(obj, GroupObject):
        return tr(f"objects.op.{obj.operation}")
    if isinstance(obj, TextObject):
        text = " ".join(str(obj.text).split())
        if len(text) > MAX_TEXT_CHARS:
            text = text[:MAX_TEXT_CHARS - 1] + "…"
        return f"« {text} »"
    if isinstance(obj, ShapeObject):
        return obj.shape_type
    if isinstance(obj, SvgPathObject):
        return tr("objects.path")
    return obj.kind


def operation_icon(palette, operation):
    """Deux carrés qui se chevauchent, la surface gardée par `operation` remplie."""
    a, b = QPainterPath(), QPainterPath()
    a.addRect(QRectF(3, 3, 18, 18))
    b.addRect(QRectF(11, 11, 18, 18))

    def draw(painter, color):
        fill = QColor(color)
        fill.setAlphaF(0.75)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawPath(boolean_ops.combine([a, b], operation))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, 1.5))
        painter.drawPath(a)
        painter.drawPath(b)
    return painted_icon(palette, draw)


def eye_icon(palette, open_eye):
    """Œil ouvert (objet affiché) ou barré (masqué)."""
    def draw(painter, color):
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        lid = QPainterPath()
        lid.moveTo(3, 16)
        lid.quadTo(16, 4, 29, 16)
        lid.quadTo(16, 28, 3, 16)
        painter.drawPath(lid)
        if open_eye:
            painter.setBrush(color)
            painter.drawEllipse(QPointF(16, 16), 4.5, 4.5)
        else:
            painter.drawLine(QPointF(5, 27), QPointF(27, 5))
    return painted_icon(palette, draw)


def ignore_icon(palette, ignored):
    """Tête laser : son faisceau pour un objet gravé, barrée de rouge pour un objet ignoré."""
    def draw(painter, color):
        head = QColor(color)
        if ignored:
            head.setAlphaF(0.45)
        painter.setPen(QPen(head, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(10, 3, 12, 11))                  # tête
        painter.drawLine(QPointF(13, 14), QPointF(19, 14))
        painter.drawLine(QPointF(14, 17), QPointF(18, 17))       # buse
        if ignored:
            painter.setPen(QPen(QColor("#ff453a"), 3))
            painter.drawLine(QPointF(5, 27), QPointF(27, 5))
            return
        painter.setPen(QPen(QColor("#ff453a"), 2.5))
        painter.drawLine(QPointF(16, 18), QPointF(16, 26))      # faisceau
        painter.setPen(QPen(QColor("#ff9f0a"), 1.5))
        for dx, dy in ((-4, 0), (4, 0), (-3, 3), (3, 3)):       # étincelle au point d'impact
            painter.drawLine(QPointF(16, 28), QPointF(16 + dx, 28 + dy))
    return painted_icon(palette, draw)


def _color_icon(color):
    pixmap = QPixmap(12, 12)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


class ObjectsPanel(QWidget):
    """Liste des objets, et boutons monter / descendre / grouper / dégrouper / opérations booléennes.

    Signaux :
    - selection_requested(objets) : objets du document choisis (un objet d'un groupe choisit le groupe) ;
    - move_requested([(groupe ou None, objet)], pas) : monter (+1) ou descendre (-1) ;
    - group_requested(opération) : grouper la sélection (boolean_ops.GROUP) ou la combiner (UNION…) ;
    - ungroup_requested() ;
    - rename_requested(objet, nom) ;
    - visibility_requested(objet, affiché) : œil (affichage seulement, l'objet reste gravé) ;
    - ignore_requested(objet) : « X », calque « Ignoré » ou retour au calque d'avant ;
    - delete_requested(groupe ou None, objet) : poubelle, supprimer l'objet (ou le retirer de son groupe).
    """

    selection_requested = pyqtSignal(list)
    move_requested = pyqtSignal(list, int)
    group_requested = pyqtSignal(str)
    ungroup_requested = pyqtSignal()
    rename_requested = pyqtSignal(object, str)
    visibility_requested = pyqtSignal(object, bool)
    ignore_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._expanded = set()
        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        headers = [""] * 5
        headers[NAME_COLUMN], headers[LAYER_COLUMN] = tr("objects.col_name"), tr("objects.col_layer")
        self.tree.setHeaderLabels(headers)
        header = self.tree.header()
        for column in range(5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch if column == NAME_COLUMN
                                        else QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False)
        self.tree.headerItem().setToolTip(EYE_COLUMN, tr("objects.eye_tip"))
        self.tree.headerItem().setToolTip(IGNORE_COLUMN, tr("objects.ignore_tip"))
        self.tree.headerItem().setToolTip(DELETE_COLUMN, tr("objects.delete_tip"))
        # L'arbre (flèche des groupes) est dans la colonne du nom, après l'œil et le laser.
        self.tree.setTreePosition(NAME_COLUMN)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        # Renommer : double-clic sur le nom seulement (l'œil, le laser et la poubelle sont des boutons).
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed)
        # Clic droit : grouper ou combiner la sélection (union, différence…), dégrouper.
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._on_double_clicked)
        self.tree.itemClicked.connect(self._on_clicked)
        self.tree.setIconSize(QSize(18, 18))
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemExpanded.connect(lambda item: self._expanded.add(id(item.data(0, OBJECT_ROLE))))
        self.tree.itemCollapsed.connect(lambda item: self._expanded.discard(id(item.data(0, OBJECT_ROLE))))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.tree, 1)
        layout.addLayout(self._buttons())
        self._icons = {
            "text": palette_icon("insert-text", self.palette()),
            "shape": palette_icon("shape-choose", self.palette()),
            "svg_path": palette_icon("format-node-curve", self.palette()),
            boolean_ops.GROUP: palette_icon("object-group", self.palette()),
        }
        for operation in boolean_ops.BOOLEAN_OPERATIONS:
            self._icons[operation] = operation_icon(self.palette(), operation)
        self._eye_icons = {shown: eye_icon(self.palette(), shown) for shown in (True, False)}
        self._ignore_icons = {ignored: ignore_icon(self.palette(), ignored) for ignored in (True, False)}
        self._delete_icon = palette_icon("edit-delete", self.palette())

    # -- construction

    def _button(self, icon, tip, slot):
        button = QToolButton()
        button.setIcon(icon)
        button.setToolTip(tip)
        button.setAutoRaise(True)
        button.clicked.connect(slot)
        return button

    def _buttons(self):
        row = QHBoxLayout()
        row.setSpacing(2)
        self.up_button = self._button(palette_icon("go-up", self.palette()), tr("objects.up_tip"),
                                      lambda: self._move(1))
        self.down_button = self._button(palette_icon("go-down", self.palette()), tr("objects.down_tip"),
                                        lambda: self._move(-1))
        self.group_button = self._button(palette_icon("object-group", self.palette()), tr("objects.group_tip"),
                                         lambda: self.group_requested.emit(boolean_ops.GROUP))
        self.ungroup_button = self._button(palette_icon("object-ungroup", self.palette()),
                                           tr("objects.ungroup_tip"), lambda: self.ungroup_requested.emit())
        # Opérations booléennes : un menu, chaque entrée avec son pictogramme.
        self.boolean_button = QToolButton()
        self.boolean_button.setIcon(operation_icon(self.palette(), boolean_ops.UNION))
        self.boolean_button.setToolTip(tr("objects.boolean_tip"))
        self.boolean_button.setAutoRaise(True)
        self.boolean_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.boolean_button)
        self.boolean_actions = {}
        for operation in boolean_ops.BOOLEAN_OPERATIONS:
            action = menu.addAction(operation_icon(self.palette(), operation), tr(f"objects.op.{operation}"))
            action.setToolTip(tr(f"objects.op.{operation}_tip"))
            action.triggered.connect(lambda _checked=False, op=operation: self.group_requested.emit(op))
            self.boolean_actions[operation] = action
        menu.setToolTipsVisible(True)
        self.boolean_button.setMenu(menu)
        for button in (self.up_button, self.down_button, self.group_button, self.ungroup_button,
                       self.boolean_button):
            row.addWidget(button)
        row.addStretch()
        return row

    def context_menu(self):
        """Menu du clic droit pour la sélection : grouper et opérations booléennes (au moins 2 objets, ou un
        groupe dont on change l'opération), dégrouper. None s'il n'y a rien à proposer."""
        objects = self.selected_objects()
        one_group = len(objects) == 1 and isinstance(objects[0], GroupObject)
        menu = QMenu(self)
        if len(objects) >= 2 or one_group:
            group = menu.addAction(self._icons[boolean_ops.GROUP], tr("objects.op.group"))
            group.triggered.connect(lambda: self.group_requested.emit(boolean_ops.GROUP))
            for operation in boolean_ops.BOOLEAN_OPERATIONS:
                action = menu.addAction(self._icons[operation], tr(f"objects.op.{operation}"))
                action.setToolTip(tr(f"objects.op.{operation}_tip"))
                action.triggered.connect(lambda _checked=False, op=operation: self.group_requested.emit(op))
        if any(isinstance(o, GroupObject) for o in objects):
            menu.addSeparator()
            menu.addAction(palette_icon("object-ungroup", self.palette()), tr("objects.ungroup")).triggered.connect(
                lambda: self.ungroup_requested.emit())
        menu.setToolTipsVisible(True)
        return menu if menu.actions() else None

    def _show_context_menu(self, position):
        menu = self.context_menu()
        if menu is not None:
            menu.exec(self.tree.viewport().mapToGlobal(position))

    # -- affichage

    def show_objects(self, objects, layer_of):
        """Remplit la liste : `objects` du dessous vers le dessus (ordre du document), affichés du dessus
        vers le dessous ; `layer_of(id)` donne le calque (nom, couleur) ou None."""
        selected = {id(o) for o in self.selected_objects()}
        self._updating = True
        try:
            self.tree.clear()
            for obj in reversed(objects):
                item = self._item(obj, None, layer_of, obj)
                self.tree.addTopLevelItem(item)
                self._add_children(item, obj, obj, layer_of)
                item.setSelected(id(obj) in selected)
        finally:
            self._updating = False
        self._update_buttons()

    def _add_children(self, item, obj, top, layer_of):
        """Objets d'un groupe, du dessus vers le dessous, et ceux de ses sous-groupes."""
        if not isinstance(obj, GroupObject):
            return
        for child in reversed(obj.children):
            child_item = self._item(child, obj, layer_of, top)
            item.addChild(child_item)
            self._add_children(child_item, child, top, layer_of)
        item.setExpanded(id(obj) in self._expanded)

    def _item(self, obj, parent, layer_of, top):
        item = QTreeWidgetItem([""] * 5)
        item.setText(NAME_COLUMN, object_label(obj))
        item.setData(0, OBJECT_ROLE, obj)
        item.setData(0, PARENT_ROLE, parent)
        item.setData(0, TOP_ROLE, top)
        icon_key = obj.operation if isinstance(obj, GroupObject) else obj.kind
        item.setIcon(NAME_COLUMN, self._icons.get(icon_key, QIcon()))
        item.setToolTip(NAME_COLUMN, tr(f"objects.op.{obj.operation}_tip") if isinstance(obj, GroupObject) else "")
        ignored, hidden = obj.is_ignored(), obj.is_hidden()
        # Œil : pour chaque objet, groupes compris (affichage seulement, l'objet reste gravé).
        item.setIcon(EYE_COLUMN, self._eye_icons[not hidden])
        item.setToolTip(EYE_COLUMN, tr("objects.show_tip" if hidden else "objects.hide_tip"))
        item.setIcon(IGNORE_COLUMN, self._ignore_icons[ignored])
        item.setIcon(DELETE_COLUMN, self._delete_icon)
        item.setToolTip(DELETE_COLUMN, tr("objects.delete_tip" if parent is None else "objects.delete_child_tip"))
        item.setToolTip(IGNORE_COLUMN, tr("objects.restore_tip" if ignored else "objects.ignore_tip"))
        if ignored:
            item.setText(LAYER_COLUMN, tr("objects.ignored_layer"))
            item.setIcon(LAYER_COLUMN, _color_icon(IGNORED_COLOR))
        else:
            layer = layer_of(obj.layer_id)
            if layer is not None:
                item.setText(LAYER_COLUMN, layer.name)
                item.setIcon(LAYER_COLUMN, _color_icon(layer.color))
        if ignored or hidden:
            # Objet masqué ou ignoré : nom grisé (et barré s'il n'est plus gravé).
            item.setForeground(NAME_COLUMN, QColor(IGNORED_COLOR))
            font = QFont(item.font(NAME_COLUMN))
            font.setStrikeOut(ignored)
            font.setItalic(hidden and not ignored)
            item.setFont(NAME_COLUMN, font)
        # Seuls les objets du dessus de la pile se renomment (un objet groupé se renomme une fois dégroupé).
        flags = item.flags()
        if parent is None:
            flags |= Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)
        return item

    def show_selection(self, objects):
        """Sélectionne dans la liste les objets choisis sur le canevas."""
        wanted = {id(o) for o in objects}
        self._updating = True
        try:
            for index in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(index)
                item.setSelected(id(item.data(0, OBJECT_ROLE)) in wanted)
                stack = [item.child(i) for i in range(item.childCount())]
                while stack:
                    child = stack.pop()
                    child.setSelected(False)
                    stack += [child.child(i) for i in range(child.childCount())]
        finally:
            self._updating = False
        self._update_buttons()

    def selected_entries(self):
        """[(groupe ou None, objet)] des lignes sélectionnées, du dessus vers le dessous."""
        entries = []
        for item in self.tree.selectedItems():
            entries.append((item.data(0, PARENT_ROLE), item.data(0, OBJECT_ROLE)))
        return entries

    def selected_objects(self):
        """Objets du document choisis : un objet d'un groupe donne le groupe du dessus de la pile."""
        objects, seen = [], set()
        for item in self.tree.selectedItems():
            target = item.data(0, TOP_ROLE)
            if id(target) not in seen:
                seen.add(id(target))
                objects.append(target)
        return objects

    def _update_buttons(self):
        entries = self.selected_entries()
        objects = self.selected_objects()
        self.up_button.setEnabled(bool(entries))
        self.down_button.setEnabled(bool(entries))
        self.group_button.setEnabled(len(objects) >= 2 or (
            len(objects) == 1 and isinstance(objects[0], GroupObject) and objects[0].is_boolean()))
        self.ungroup_button.setEnabled(any(isinstance(o, GroupObject) for o in objects))
        self.boolean_button.setEnabled(len(objects) >= 2 or (
            len(objects) == 1 and isinstance(objects[0], GroupObject)))

    # -- actions de l'utilisateur

    def _on_selection_changed(self):
        self._update_buttons()
        if not self._updating:
            self.selection_requested.emit(self.selected_objects())

    def _on_clicked(self, item, column):
        obj, parent = item.data(0, OBJECT_ROLE), item.data(0, PARENT_ROLE)
        if column == EYE_COLUMN:
            self.visibility_requested.emit(obj, obj.is_hidden())
        elif column == IGNORE_COLUMN:
            self.ignore_requested.emit(obj)
        elif column == DELETE_COLUMN:
            self.delete_requested.emit(parent, obj)

    def _on_double_clicked(self, item, column):
        if column == NAME_COLUMN and item.flags() & Qt.ItemFlag.ItemIsEditable:
            self.tree.editItem(item, NAME_COLUMN)

    def _on_item_changed(self, item, column):
        if self._updating or column != NAME_COLUMN:
            return
        obj = item.data(0, OBJECT_ROLE)
        name = item.text(NAME_COLUMN).strip()
        if name != object_label(obj):
            self.rename_requested.emit(obj, name)

    def _move(self, step):
        entries = self.selected_entries()
        if entries:
            self.move_requested.emit(entries, step)
