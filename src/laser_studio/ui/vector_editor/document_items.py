"""Correspondance entre les objets d'un VectorDocument et leurs éléments graphiques dans une scène Qt : un
élément par objet, créé, redessiné ou retiré quand le document le signale, empilé dans l'ordre du document
(le dernier objet au-dessus), et la sélection exprimée en objets. Sans vue : testable avec une simple scène.

    items = DocumentItems(document, scene, make_item=lambda obj: VectorGraphicsItem(obj, layers, canvas))
    document.add(obj)
    items.item_for(obj)          # son VectorGraphicsItem
    items.select([obj])          # sélection exacte, sans signal de la scène
"""
from laser_studio.ui.vector_editor.item import VectorGraphicsItem


class DocumentItems:
    """Éléments graphiques des objets de `document` dans `scene` ; `make_item(objet)` crée l'élément d'un
    objet (il n'est pas encore dans la scène)."""

    def __init__(self, document, scene, make_item):
        self.document = document
        self.scene = scene
        self._make_item = make_item
        self._items = {}                  # id(objet) -> élément : un objet n'est pas forcément hachable
        document.object_added.connect(self._add)
        document.object_removed.connect(self._remove)
        document.objects_changed.connect(self.refresh)
        document.objects_reset.connect(self._reset)
        document.order_changed.connect(self._apply_order)

    # -- lecture

    def item_for(self, obj):
        """Élément graphique de `obj`, ou None."""
        return self._items.get(id(obj))

    def all(self):
        """Éléments de tous les objets, dans l'ordre du document."""
        return [self._items[id(obj)] for obj in self.document.objects if id(obj) in self._items]

    def selected(self):
        """Éléments sélectionnés (les fonds de la scène ne comptent pas)."""
        return [item for item in self.scene.selectedItems() if isinstance(item, VectorGraphicsItem)]

    def selected_object(self):
        """(élément, objet) du premier élément sélectionné, ou (None, None)."""
        selected = self.selected()
        return (selected[0], selected[0].obj) if selected else (None, None)

    # -- sélection et affichage

    def select(self, objects):
        """Sélectionne exactement `objects`, sans que la scène émette selectionChanged à chaque élément
        (l'appelant prévient une seule fois). Renvoie les objets sélectionnés, dans l'ordre du document."""
        wanted = {id(obj) for obj in objects}
        blocked = self.scene.blockSignals(True)
        try:
            for item in self.selected():
                item.setSelected(False)
            for obj in objects:
                item = self.item_for(obj)
                if item is not None:
                    item.setSelected(True)
        finally:
            self.scene.blockSignals(blocked)
        return [obj for obj in self.document.objects if id(obj) in wanted]

    def select_all_active(self):
        """Ctrl+A : tous les objets, sauf les masqués ou ignorés (ils se sélectionnent depuis la liste)."""
        for item in self.all():
            if not item.inactive:
                item.setSelected(True)

    def refresh(self, objects=None):
        """Redessine les éléments de `objects` (tous par défaut) : objets modifiés, calque recoloré."""
        for obj in self.document.objects if objects is None else objects:
            item = self.item_for(obj)
            if item is not None:
                item.refresh()

    # -- suivi du document

    def _add(self, obj, reorder=True):
        item = self._make_item(obj)
        self.scene.addItem(item)
        self._items[id(obj)] = item
        if reorder:
            self._apply_order()

    def _remove(self, obj):
        item = self._items.pop(id(obj), None)
        if item is not None:
            try:
                self.scene.removeItem(item)
            except RuntimeError:                       # déjà détruit avec la scène
                pass

    def _reset(self):
        """Tout le document a changé (annuler, refaire, charger) : de nouveaux éléments."""
        for item in list(self._items.values()):
            self.scene.removeItem(item)
        self._items = {}
        for obj in self.document.objects:
            self._add(obj, reorder=False)
        self._apply_order()                            # une fois, pas après chaque objet

    def _apply_order(self):
        for index, obj in enumerate(self.document.objects):
            item = self.item_for(obj)
            if item is not None:
                item.setZValue(index)
