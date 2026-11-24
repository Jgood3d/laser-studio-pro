"""Liste des objets de l'éditeur vectoriel (ObjectsPanel), à droite du canevas, à la manière de
l'outliner de Blender : du dessus de la pile vers le dessous, un groupe déplié montre ses objets.

Simple vue : elle affiche ce qu'on lui donne (show_objects, show_selection) et émet des signaux quand
l'utilisateur agit ; le contrôleur de l'éditeur modifie le document.

    panel = ObjectsPanel()
    panel.selection_requested.connect(canvas.select_objects)
    panel.move_requested.connect(editor.move_objects)
    document.order_changed.connect(lambda: panel.show_objects(document.objects, layers.get))
"""
from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QMenu, QToolButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from laser_studio.i18n import tr
from laser_studio.models.vector_objects import GroupObject, ShapeObject, SvgPathObject, TextObject
from laser_studio.ui.utils import painted_icon, palette_icon
from laser_studio.vector import boolean_ops

OBJECT_ROLE = Qt.ItemDataRole.UserRole
PARENT_ROLE = Qt.ItemDataRole.UserRole + 1
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
    - rename_requested(objet, nom).
    """

    selection_requested = pyqtSignal(list)
    move_requested = pyqtSignal(list, int)
    group_requested = pyqtSignal(str)
    ungroup_requested = pyqtSignal()
    rename_requested = pyqtSignal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._expanded = set()
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels([tr("objects.col_name"), tr("objects.col_layer")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setStretchLastSection(False)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                  | QAbstractItemView.EditTrigger.EditKeyPressed)
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

    # -- affichage

    def show_objects(self, objects, layer_of):
        """Remplit la liste : `objects` du dessous vers le dessus (ordre du document), affichés du dessus
        vers le dessous ; `layer_of(id)` donne le calque (nom, couleur) ou None."""
        selected = {id(o) for o in self.selected_objects()}
        self._updating = True
        try:
            self.tree.clear()
            for obj in reversed(objects):
                item = self._item(obj, None, layer_of)
                self.tree.addTopLevelItem(item)
                if isinstance(obj, GroupObject):
                    for child in reversed(obj.children):
                        item.addChild(self._item(child, obj, layer_of))
                    item.setExpanded(id(obj) in self._expanded)
                item.setSelected(id(obj) in selected)
        finally:
            self._updating = False
        self._update_buttons()

    def _item(self, obj, parent, layer_of):
        item = QTreeWidgetItem([object_label(obj), ""])
        item.setData(0, OBJECT_ROLE, obj)
        item.setData(0, PARENT_ROLE, parent)
        icon_key = obj.operation if isinstance(obj, GroupObject) else obj.kind
        item.setIcon(0, self._icons.get(icon_key, QIcon()))
        item.setToolTip(0, tr(f"objects.op.{obj.operation}_tip") if isinstance(obj, GroupObject) else "")
        layer = layer_of(obj.layer_id)
        if layer is not None:
            item.setText(1, layer.name)
            item.setIcon(1, _color_icon(layer.color))
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
                for child in range(item.childCount()):
                    item.child(child).setSelected(False)
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
        """Objets du document choisis : un objet d'un groupe donne le groupe."""
        objects, seen = [], set()
        for parent, obj in self.selected_entries():
            target = parent if parent is not None else obj
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

    def _on_item_changed(self, item, column):
        if self._updating or column != 0:
            return
        obj = item.data(0, OBJECT_ROLE)
        name = item.text(0).strip()
        if name != object_label(obj):
            self.rename_requested.emit(obj, name)

    def _move(self, step):
        entries = self.selected_entries()
        if entries:
            self.move_requested.emit(entries, step)
